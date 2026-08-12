import hashlib
from datetime import datetime, timezone
from typing import Any

from neo4j import Session as Neo4jSession
from sqlalchemy.orm import Session as PgSession

from app.core.tool_base import NormalizedFinding
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.target import Target
from app.services import risk_scoring


def make_content_hash(f: NormalizedFinding) -> str:
    if f.source == "instaloader" and f.extra_metadata.get("field") == "post_image":
        key = f"{f.source}:post_image:{f.extra_metadata.get('shortcode')}"
    else:
        key = f"{f.source}:{f.raw_value}:{f.source_url}"
    return hashlib.sha256(key.encode()).hexdigest()

def store_findings(
    tool_id: str,
    target_label: str,
    findings: list[NormalizedFinding],
    db: PgSession,
) -> dict[str, Any]:
    target = db.query(Target).filter(Target.label == target_label).first()
    if not target:
        target = Target(label=target_label)
        db.add(target)
        db.flush()

    scan = Scan(target_id=target.id, tool_used=tool_id, finished_at=datetime.now(timezone.utc))
    db.add(scan)
    db.flush()

    # compute hashes up front so we can both dedup and reuse them below
    for f in findings:
        f.content_hash = make_content_hash(f)

    existing_hashes = {
        row.content_hash
        for row in db.query(Finding.content_hash).filter(Finding.target_id == target.id).all()
    }

    new_findings = [f for f in findings if f.content_hash not in existing_hashes]
    skipped = len(findings) - len(new_findings)

    platform_count = len(findings)   # keep denominator based on the full scan, not just new ones
    finding_rows = []
    seen_this_batch = set()
    for f in new_findings:
        if f.content_hash in seen_this_batch:
            continue  # guard against dupes within the same tool run
        seen_this_batch.add(f.content_hash)

        scores = risk_scoring.compute_scores(f.category, platform_count)
        finding_rows.append(
            Finding(
                target_id=target.id,
                scan_id=scan.id,
                source=f.source,
                source_url=f.source_url,
                raw_value=f.raw_value,
                category=f.category,
                content_hash=f.content_hash,
                http_status=f.http_status,
                response_time_s=f.response_time_s,
                extra_metadata={**f.extra_metadata, "tool": tool_id},
                **scores,
            )
        )

    db.add_all(finding_rows)
    db.commit()

    return {
        "target_id": str(target.id),
        "scan_id": str(scan.id),
        "findings_stored": len(finding_rows),
        "findings_skipped_duplicate": skipped,
    }


def store_graph(
    tool_id: str,
    target_label: str,
    findings: list[NormalizedFinding],
    session: Neo4jSession,
    identifier_type: str = "username",   # NEW
) -> dict[str, Any]:
    """
    (Target)-[:HAS_IDENTIFIER]->(Identifier {value, type})-[:FOUND_ON]->(Platform)
    Identifier is now keyed on (value, type) so a target can have multiple
    identifier types (username, email, domain, ...) without collisions.
    """
    session.run(
        """
        MERGE (t:Target {name: $target_label})
        ON CREATE SET t.created_at = datetime()
        MERGE (i:Identifier {value: $target_label, type: $identifier_type})
        MERGE (t)-[:HAS_IDENTIFIER]->(i)
        """,
        target_label=target_label,
        identifier_type=identifier_type,
    )

    for f in findings:
        session.run(
            """
            MATCH (i:Identifier {value: $target_label, type: $identifier_type})
            MERGE (p:Platform {name: $platform})
            MERGE (i)-[r:FOUND_ON]->(p)
            ON CREATE SET
                r.url = $url,
                r.discovered_by = [$tool_id],
                r.first_seen = datetime()
            ON MATCH SET
                r.discovered_by = CASE
                    WHEN $tool_id IN r.discovered_by THEN r.discovered_by
                    ELSE r.discovered_by + $tool_id
                END
            """,
            target_label=target_label,
            identifier_type=identifier_type,
            platform=f.source,
            url=f.source_url,
            tool_id=tool_id,
        )

    return {"target": target_label, "platforms_linked": len(findings)}