
# OSINT Footprint Map

🏗️🚧 **Work in progress** — built for CHAKRAVYUH 1.0 (PS ID: GITACVPS001, "OSINT: Mapping the Invisible Footprint").

A multi-tool OSINT aggregation platform that takes a username, email, or image, runs it through a set of pluggable OSINT tools, normalizes the results, stores them in Postgres, and mirrors them into a Neo4j graph so exposure across platforms can be explored visually and correlated.

## What it does

Given a target identifier, the backend runs one or more OSINT tools against it and returns a unified set of findings:

- **Sherlock** — username enumeration across social platforms
- **Maigret** — deeper username enumeration with profile metadata (bio, follower count, verification status) and a usefulness-scoring heuristic to filter out dead/search-redirect results
- **EXIF Extractor** — pulls GPS coordinates and device metadata out of an image (by URL or direct upload)
- **HaveIBeenPwned** — checks an email against known data breaches

Every tool speaks the same contract (`NormalizedFinding` in, stored the same way out), so new tools can be dropped into `backend/app/tools/<name>/` and are auto-discovered and mounted — no changes needed to `main.py`.

## Architecture

```
frontend/   React + Vite + TypeScript UI, force-directed graph view
backend/    FastAPI, auto-discovers tools under app/tools/
  app/tools/<name>/router.py   -> defines TOOL_ID + APIRouter, auto-mounted
  app/tools/<name>/service.py  -> does the actual scan, returns NormalizedFinding list
  app/core/registry.py         -> plugin discovery
  app/db/postgres.py           -> relational storage (targets, scans, findings)
  app/db/neo4j.py              -> graph storage (for cross-platform correlation)
  app/services/storage.py      -> dedup (content hash) + writes to both stores
  app/services/risk_scoring.py -> exposure risk severity scoring
```

Postgres holds the structured record of every target/scan/finding. Neo4j holds the same findings as a graph so you can see, e.g., how a username, an email, and a leaked credential all connect back to one entity. Redis and Qdrant are provisioned in `docker-compose.yml` for future use (caching / vector similarity search) but nothing currently uses them.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

## Setup

**1. Start infrastructure**
```bash
docker compose up -d
```
Brings up Postgres (`:5432`), Neo4j (`:7474` browser / `:7687` bolt), Redis (`:6379`), and Qdrant (`:6333`).

**2. Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python init_db.py             # creates Postgres tables
uvicorn app.main:app --reload
```
API available at `http://localhost:8000`. `sherlock` and `maigret` are invoked as CLI subprocesses (installed via `sherlock-project` and `maigret` in requirements.txt) — make sure they're on your `PATH` inside the venv.

**3. Frontend**
```bash
cd frontend
npm install
npm run dev
```
UI available at `http://localhost:5173`.

**4. Verify**
```bash
curl http://localhost:8000/health
```
Should return the list of auto-discovered tools.

## Environment variables

Copy `.env.example` → `.env` and fill in:

| Variable | Description |
|---|---|
| `POSTGRES_URL` | SQLAlchemy connection string |
| `NEO4J_URI` | e.g. `bolt://neo4j:7687` |
| `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j credentials |
| `SHERLOCK_CMD` | override if `sherlock` isn't on PATH (default: `sherlock`) |
| `MAIGRET_CMD` | override if `maigret` isn't on PATH (default: `maigret`) |
| `HIBP_API_KEY` | required for the HaveIBeenPwned tool — get one at haveibeenpwned.com/API/Key |

> ⚠️ Never commit `.env`. If real credentials were ever committed, rotate them and scrub git history.

## API overview

| Endpoint | Description |
|---|---|
| `GET /health` | service + loaded tools |
| `GET /health/postgres`, `/health/neo4j` | DB connectivity checks |
| `POST /scan/username/{username}` | run Sherlock |
| `POST /maigret/username/{username}` | run Maigret |
| `POST /exif_extractor/image_url/{url}` / `POST /exif_extractor/upload` | run EXIF extraction |
| `POST /haveibeenpwned/email/{email}` | run breach check |
| `GET /scan/history` | all previously scanned targets |
| `GET /{tool}/graph/{value}` | graph view of a target's findings |

## Roadmap / not built yet

- Reverse OSINT (detecting who is tracking the user's data)
- Autonomous/self-learning scanning agent (scheduled scans, pattern learning)
- Risk severity scoring is scaffolded (`risk_scoring.py`, score columns on `Finding`) but not fully computed everywhere
- Video/audio signal analysis
- More tools: code-repository leak scanning, reverse image search

## Ethics & scope

This project only aggregates **publicly accessible** information via existing OSINT tools and public APIs (Sherlock, Maigret, HaveIBeenPwned, EXIF from user-supplied images). It is intended for personal exposure auditing and security research, not surveillance of third parties without consent.