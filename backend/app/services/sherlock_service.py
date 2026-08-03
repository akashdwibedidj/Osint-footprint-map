import asyncio
import csv
import subprocess
import tempfile
from pathlib import Path


class SherlockService:
    def __init__(self, sherlock_cmd: str = "sherlock"):
        self.sherlock_cmd = sherlock_cmd

    def _run_sherlock_sync(self, username: str, timeout: int) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                *self.sherlock_cmd.split(),
                username,
                "--csv",
                "--folderoutput", tmpdir,
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                raise TimeoutError(f"Sherlock scan for '{username}' timed out")

            csv_path = Path(tmpdir) / f"{username}.csv"

            if not csv_path.exists():
                return {
                    "username": username,
                    "found": [],
                    "raw_stdout": proc.stdout.decode(errors="ignore"),
                    "raw_stderr": proc.stderr.decode(errors="ignore"),
                }

            found_sites = []
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("exists") == "Claimed":
                        found_sites.append({
                            "site": row.get("name"),
                            "url": row.get("url_user"),
                            "http_status": row.get("http_status"),
                            "response_time_s": row.get("response_time_s"),
                        })

            return {
                "username": username,
                "found": found_sites,
                "total_found": len(found_sites),
            }

    async def search_username(self, username: str, timeout: int = 120) -> dict:
        # Run the blocking subprocess call in a thread so it works fine
        # under Windows' default asyncio event loop (which can't run
        # subprocesses directly).
        return await asyncio.to_thread(self._run_sherlock_sync, username, timeout)


sherlock_service = SherlockService()  