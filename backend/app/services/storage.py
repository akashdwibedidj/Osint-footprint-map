"""
Generic storage layer. ANY tool that returns list[NormalizedFinding]
gets Postgres + Neo4j storage for free -- no per-tool storage function
needed. This replaces the old scan_storage.py / neo4j_storage.py
pattern of writing a new store_X_findings()/store_X_graph() per tool.
"""

from datetime import datetime, timezone
from typing import Any

from neo4j import Session as Neo4jSession
from sqlalchemy.orm import Session as PgSession

from app.core.tool_base import NormalizedFinding
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.target import Target
from app.services import risk_scoring


def store_findings(
    tool_id: str,
    target_label: str,
    findings: list[NormalizedFinding],
    db: PgSession,
) -> dict[str, Any]:
    """
    Get-or-create Target, create a Scan for this tool run, insert one
    Finding row per result -- with real risk scores from risk_scoring.py
    instead of the old "unscored" placeholder.
    """
    target = db.query(Target).filter(Target.label == target_label).first()
    if not target:
        target = Target(label=target_label)
        db.add(target)
        db.flush()

    scan = Scan(target_id=target.id, tool_used=tool_id, finished_at=datetime.now(timezone.utc))
    db.add(scan)
    db.flush()

    platform_count = len(findings)
    finding_rows = []
    for f in findings:
        scores = risk_scoring.compute_scores(f.category, platform_count)
        finding_rows.append(
            Finding(
                target_id=target.id,
                scan_id=scan.id,
                source=f.source,
                source_url=f.source_url,
                raw_value=f.raw_value,
                category=f.category,
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
    }


def store_graph(
    tool_id: str,
    target_label: str,
    findings: list[NormalizedFinding],
    session: Neo4jSession,
) -> dict[str, Any]:
    """
    Pushes findings into Neo4j as:
      (Target)-[:HAS_IDENTIFIER]->(Identifier)-[:FOUND_ON]->(Platform)
    Uses MERGE so re-running a scan, or running a *different* tool
    against the same target, correlates onto the same graph instead
    of creating duplicates. `discovered_by` on each edge tracks which
    tool(s) found that platform, so once you add Osintgram/others you
    can see cross-tool corroboration for free.
    """
    session.run(
        """
        MERGE (t:Target {name: $target_label})
        ON CREATE SET t.created_at = datetime()
        MERGE (i:Identifier {value: $target_label})
        MERGE (t)-[:HAS_IDENTIFIER]->(i)
        """,
        target_label=target_label,
    )

    for f in findings:
        session.run(
            """
            MATCH (i:Identifier {value: $target_label})
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
            platform=f.source,
            url=f.source_url,
            tool_id=tool_id,
        )

    return {"target": target_label, "platforms_linked": len(findings)}
