import asyncio
import os
import time

import requests

from app.models.finding import ExposureCategory
from app.services.storage import NormalizedFinding

HIBP_API_KEY = os.environ.get("HIBP_API_KEY", "")
HIBP_BASE_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"
USER_AGENT = "OSINT-Aggregator (contact: set-your-contact-email-here)"


def _query_hibp(email: str) -> tuple[list[dict], int | None, float]:
    """Blocking call to the HIBP breachedaccount endpoint. Returns (breaches, http_status, elapsed_s)."""
    headers = {
        "hibp-api-key": HIBP_API_KEY,
        "User-Agent": USER_AGENT,
    }
    params = {"truncateResponse": "false"}

    start = time.monotonic()
    resp = requests.get(
        f"{HIBP_BASE_URL}/{email}",
        headers=headers,
        params=params,
        timeout=15,
    )
    elapsed = time.monotonic() - start

    if resp.status_code == 404:
        # No breaches found — not an error condition
        return [], resp.status_code, elapsed
    if resp.status_code == 401:
        raise RuntimeError("HIBP API key missing or invalid (HTTP 401)")
    if resp.status_code == 429:
        raise RuntimeError("HIBP rate limit exceeded (HTTP 429) — back off and retry")
    resp.raise_for_status()

    return resp.json(), resp.status_code, elapsed


async def run(target_value: str, **kwargs) -> list[NormalizedFinding]:
    """
    target_value: an email address to check against known breaches via HIBP v3.
    """
    if not HIBP_API_KEY:
        raise RuntimeError(
            "HIBP_API_KEY is not set. Obtain a key from "
            "https://haveibeenpwned.com/API/Key and set it in the environment."
        )

    breaches, http_status, elapsed = await asyncio.to_thread(_query_hibp, target_value)

    findings: list[NormalizedFinding] = []
    for breach in breaches:
        findings.append(
            NormalizedFinding(
                source="haveibeenpwned",
                source_url=f"https://haveibeenpwned.com/PwnedWebsites#{breach.get('Name', '')}",
                raw_value=breach.get("Name", "unknown_breach"),
                category=ExposureCategory.CREDENTIAL,
                http_status=http_status,
                response_time_s=elapsed,
                extra_metadata={
                    "breach_title": breach.get("Title"),
                    "breach_domain": breach.get("Domain"),
                    "breach_date": breach.get("BreachDate"),
                    "added_date": breach.get("AddedDate"),
                    "pwn_count": breach.get("PwnCount"),
                    "data_classes": breach.get("DataClasses", []),
                    "is_verified": breach.get("IsVerified"),
                    "is_sensitive": breach.get("IsSensitive"),
                    "is_spam_list": breach.get("IsSpamList"),
                },
            )
        )

    return findings