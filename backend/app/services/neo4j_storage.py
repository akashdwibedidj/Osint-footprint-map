from neo4j import Session
from typing import List, Dict, Any


def store_sherlock_graph(username: str, sherlock_result: dict, session: Session) -> dict:
    """
    Pushes sherlock findings into Neo4j as a graph:
    (Target)-[:HAS_IDENTIFIER]->(Identifier)-[:FOUND_ON]->(Platform)
    Uses MERGE so re-running the same scan won't create duplicate nodes.
    """

    found_sites = sherlock_result.get("found", [])

    query = """
    MERGE (t:Target {name: $username})
    MERGE (i:Identifier {value: $username})
    MERGE (t)-[:HAS_IDENTIFIER]->(i)
    WITH i
    UNWIND $sites AS site
    MERGE (p:Platform {name: site.site})
    MERGE (i)-[:FOUND_ON {url: site.url}]->(p)
    """

    session.run(query, username=username, sites=found_sites)

    return {
        "target": username,
        "platforms_linked": len(found_sites),
    }

def store_maigret_graph(username: str, findings: List[Dict[str, Any]], session: Session) -> dict:
    """
    Pushes Maigret findings into Neo4j using same graph model as Sherlock.
    (Target)-[:HAS_IDENTIFIER]->(Identifier)-[:FOUND_ON]->(Platform)
    Uses MERGE so re-running won't duplicate nodes.
    """
    session.run(
        """
        MERGE (t:Target {name: $username})
        ON CREATE SET t.created_at = datetime()
        """,
        username=username,
    )

    for f in findings:
        platform = f["platform"]
        url_user = f["url_user"]

        session.run(
            """
            MATCH (t:Target {name: $username})
            MERGE (i:Identifier {value: $username})
            MERGE (p:Platform {name: $platform})
            MERGE (t)-[:HAS_IDENTIFIER]->(i)
            MERGE (i)-[r:FOUND_ON]->(p)
            ON CREATE SET r.url = $url, r.discovered_by = ['maigret'], r.first_seen = datetime()
            ON MATCH SET r.discovered_by = CASE 
                WHEN 'maigret' IN r.discovered_by THEN r.discovered_by 
                ELSE r.discovered_by + 'maigret' 
            END
            """,
            username=username,
            platform=platform,
            url=url_user,
        )

    return {"nodes_created": len(findings)}