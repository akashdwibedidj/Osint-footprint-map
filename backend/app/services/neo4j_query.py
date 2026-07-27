def get_target_graph(username: str, session) -> dict:
    """
    Returns nodes + edges for a target's footprint graph:
    (Target)-[:HAS_IDENTIFIER]->(Identifier)-[:FOUND_ON]->(Platform)
    """

    query = """
    MATCH (t:Target {name: $username})-[:HAS_IDENTIFIER]->(i:Identifier)
    OPTIONAL MATCH (i)-[r:FOUND_ON]->(p:Platform)
    RETURN t, i, collect(r) AS rels, collect(p) AS platforms
    """

    result = session.run(query, username=username)
    record = result.single()

    if not record or record["t"] is None:
        return {"nodes": [], "edges": []}

    nodes = []
    edges = []

    target_node = record["t"]
    identifier_node = record["i"]
    platforms = record["platforms"]
    rels = record["rels"]

    nodes.append({
        "id": f"target-{target_node['name']}",
        "label": target_node["name"],
        "type": "Target",
    })
    nodes.append({
        "id": f"identifier-{identifier_node['value']}",
        "label": identifier_node["value"],
        "type": "Identifier",
    })
    edges.append({
        "source": f"target-{target_node['name']}",
        "target": f"identifier-{identifier_node['value']}",
        "type": "HAS_IDENTIFIER",
    })

    for platform, rel in zip(platforms, rels):
        if platform is None:
            continue
        platform_id = f"platform-{platform['name']}"
        nodes.append({
            "id": platform_id,
            "label": platform["name"],
            "type": "Platform",
        })
        edges.append({
            "source": f"identifier-{identifier_node['value']}",
            "target": platform_id,
            "type": "FOUND_ON",
            "url": rel.get("url") if rel else None,
        })

    return {"nodes": nodes, "edges": edges}