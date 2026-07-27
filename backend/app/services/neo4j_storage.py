from neo4j import Session


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