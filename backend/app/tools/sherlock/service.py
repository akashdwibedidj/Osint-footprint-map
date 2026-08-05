import asyncio
import csv
import subprocess
import tempfile
from pathlib import Path

from app.config import settings
from app.core.tool_base import NormalizedFinding
from app.models.finding import ExposureCategory


def _run_sync(username: str, timeout: int) -> list[NormalizedFinding]:
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [*settings.sherlock_cmd.split(), username, "--csv", "--folderoutput", tmpdir]

        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Sherlock scan for '{username}' timed out")
        except FileNotFoundError:
            raise RuntimeError(
                f"Sherlock command '{settings.sherlock_cmd}' not found. "
                "Install it or set SHERLOCK_CMD in your .env."
            )

        csv_path = Path(tmpdir) / f"{username}.csv"
        if not csv_path.exists():
            return []

        findings = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("exists") != "Claimed":
                    continue
                http_status = row.get("http_status")
                response_time = row.get("response_time_s")
                findings.append(
                    NormalizedFinding(
                        source=row.get("name", ""),
                        source_url=row.get("url_user", ""),
                        raw_value=username,
                        category=ExposureCategory.PERSONAL_IDENTIFIER,
                        http_status=int(http_status) if http_status and http_status.isdigit() else None,
                        response_time_s=float(response_time) if response_time else None,
                    )
                )
        return findings


async def run(username: str, timeout: int = 120) -> list[NormalizedFinding]:
    # Run the blocking subprocess call in a thread so it works fine
    # under Windows' default asyncio event loop (which can't run
    # subprocesses directly).
    return await asyncio.to_thread(_run_sync, username, timeout)
