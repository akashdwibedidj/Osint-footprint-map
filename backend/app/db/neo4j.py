from neo4j import GraphDatabase
from app.config import settings

driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password)
)

def get_neo4j_session():
    session = driver.session()
    try:
        yield session
    finally:
        session.close()

def close_neo4j_driver():
    driver.close()