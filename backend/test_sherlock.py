import asyncio
import sys

from app.services.sherlock_service import sherlock_service
from app.services.scan_storage import store_sherlock_results
from app.services.neo4j_storage import store_sherlock_graph
from app.db.postgres import SessionLocal
from app.db.neo4j import driver


async def main(username: str):
    result = await sherlock_service.search_username(username)
    print(f"Sherlock found {result['total_found']} accounts.")

    # Store in Postgres
    db = SessionLocal()
    try:
        saved = store_sherlock_results(username, result, db)
        print("Stored in Postgres:", saved)
    finally:
        db.close()

    # Store in Neo4j
    with driver.session() as session:
        graph_result = store_sherlock_graph(username, result, session)
        print("Stored in Neo4j:", graph_result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_sherlock.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    asyncio.run(main(username))