def get_target_graph(username: str, session) -> dict:
    """
    Returns nodes + edges for a target's footprint graph:
    (Target)-[:HAS_IDENTIFIER]->(Identifier)-[:FOUND_ON]->(Platform)
    A target may now have multiple Identifiers (different types).
    """
    query = """
    MATCH (t:Target {name: $username})-[:HAS_IDENTIFIER]->(i:Identifier)
    OPTIONAL MATCH (i)-[r:FOUND_ON]->(p:Platform)
    RETURN t, i, r, p
    """

    result = session.run(query, username=username)
    records = list(result)

    if not records:
        return {"nodes": [], "edges": []}

    nodes: dict[str, dict] = {}
    edges = []

    target_node = records[0]["t"]
    target_id = f"target-{target_node['name']}"
    nodes[target_id] = {"id": target_id, "label": target_node["name"], "type": "Target"}

    for rec in records:
        i = rec["i"]
        identifier_id = f"identifier-{i['type']}-{i['value']}"
        if identifier_id not in nodes:
            nodes[identifier_id] = {
                "id": identifier_id,
                "label": i["value"],
                "type": "Identifier",
                "identifier_type": i["type"],
            }
            edges.append({"source": target_id, "target": identifier_id, "type": "HAS_IDENTIFIER"})

        p, r = rec["p"], rec["r"]
        if p is None:
            continue
        platform_id = f"platform-{p['name']}"
        if platform_id not in nodes:
            nodes[platform_id] = {"id": platform_id, "label": p["name"], "type": "Platform"}
        edges.append({
            "source": identifier_id,
            "target": platform_id,
            "type": "FOUND_ON",
            "url": r.get("url") if r else None,
            "discovered_by": r.get("discovered_by") if r else None,
        })

    return {"nodes": list(nodes.values()), "edges": edges}