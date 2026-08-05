"""
Shared contract every OSINT tool plugin must speak.

A tool's service module only has to do ONE thing: take a target
(username, email, whatever) and return a list of NormalizedFinding.
Everything downstream (Postgres storage, Neo4j graph storage, risk
scoring, the /history and /graph endpoints) is generic and already
handles any tool that follows this contract. Adding a new tool never
requires touching storage.py, main.py, or any other tool's code.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.models.finding import ExposureCategory


@dataclass
class NormalizedFinding:
    source: str                    # e.g. "GitHub", "Instagram"
    source_url: str                # profile / page URL
    raw_value: str                 # the identifier that was searched (username, email, ...)
    category: ExposureCategory = ExposureCategory.PERSONAL_IDENTIFIER
    http_status: Optional[int] = None
    response_time_s: Optional[float] = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)


class ToolPlugin:
    """
    Optional marker/base class for a tool's router module. Not required
    at runtime (the registry works off module attributes), but useful
    for editors/type checkers and as documentation of the contract.

    Every app/tools/<name>/router.py must define:
        TOOL_ID: str            -> unique tool id, e.g. "sherlock"
        router: fastapi.APIRouter
    """

    TOOL_ID: str
