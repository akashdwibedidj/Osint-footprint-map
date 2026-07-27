"""
Run this once (or whenever models change) to create/update tables in Postgres.

Usage:
    python init_db.py
"""

from app.db.postgres import Base, engine
from app.models import target, scan, finding


def init_db():
    print("Creating tables in Postgres...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created (or already existed):")
    for table in Base.metadata.tables:
        print(f"  - {table}")


if __name__ == "__main__":
    init_db()