from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.registry import register_tools
from app.db.neo4j import close_neo4j_driver, get_neo4j_session
from app.db.postgres import Base, engine, get_db
from app.models import finding, scan, target  # noqa: F401 (ensures tables are registered)
from app.routers import core_router

app = FastAPI(title="OSINT Footprint Map")

app.include_router(core_router.router)
registered_tools = register_tools(app)  # auto-mounts every app/tools/<name>/router.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.on_event("shutdown")
def shutdown():
    close_neo4j_driver()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tools_loaded": [t.tool_id for t in registered_tools],
    }


@app.get("/health/postgres")
def health_postgres(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"postgres": "connected"}


@app.get("/health/neo4j")
def health_neo4j(session=Depends(get_neo4j_session)):
    result = session.run("RETURN 1 AS ok")
    return {"neo4j": result.single()["ok"] == 1}
