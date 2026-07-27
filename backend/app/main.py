from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.postgres import get_db, engine, Base
from app.db.neo4j import get_neo4j_session, close_neo4j_driver
from app.routers import sherlock_router
from app.models import target, scan, finding

app = FastAPI(title="OSINT Footprint Map")
app.include_router(sherlock_router.router)

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
    return {"status": "ok"}

@app.get("/health/postgres")
def health_postgres(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"postgres": "connected"}

@app.get("/health/neo4j")
def health_neo4j(session=Depends(get_neo4j_session)):
    result = session.run("RETURN 1 AS ok")
    return {"neo4j": result.single()["ok"] == 1}