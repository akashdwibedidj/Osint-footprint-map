import asyncio
import tempfile
import re
from pathlib import Path

class SherlockService:
    def __init__(self, sherlock_cmd: str = "sherlock"):
        self.sherlock_cmd = sherlock_cmd

    async def search_username(self, username: str, timeout: int = 60) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / f"{username}.txt"

            cmd = [
                *self.sherlock_cmd.split(),
                username,
                "--print-found",
                "--output", str(output_file),
                "--timeout", "10",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError(f"Sherlock scan for '{username}' timed out")

            if not output_file.exists():
                return {
                    "username": username,
                    "found": [],
                    "raw_stdout": stdout.decode(errors="ignore"),
                    "raw_stderr": stderr.decode(errors="ignore"),
                }

            found_sites = []
            with open(output_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    match = re.match(r"\[\+\]\s*([^:]+):\s*(.+)", line)
                    if match:
                        site, url = match.groups()
                        found_sites.append({"site": site.strip(), "url": url.strip()})

            return {
                "username": username,
                "found": found_sites,
                "total_found": len(found_sites),
            }


sherlock_service = SherlockService()