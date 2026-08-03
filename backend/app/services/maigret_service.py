import asyncio
import csv
import os
import shutil
import subprocess
import tempfile
from typing import List, Dict, Any

MAIGRET_PATH = r"F:\Projects\OSINT_footprint_mapping_project\OSINT_footprint_mapping\backend\venv\Scripts\maigret.exe"


def run_maigret(username: str) -> List[Dict[str, Any]]:
    temp_dir = tempfile.mkdtemp(prefix="maigret_")
    try:
        cmd = [
            MAIGRET_PATH,
            username,
            "--csv",
            "--folderoutput", temp_dir,
            "--dns-resolver", "threaded",
            "--no-recursion",
            "--no-extracting",
            "--no-color",
        ]

        # Set UTF-8 encoding environment to prevent cp1252 crash
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        if result.returncode != 0 and "Too many errors" not in result.stderr:
            raise RuntimeError(f"Maigret failed: {result.stderr}")

        report_path = os.path.join(temp_dir, f"report_{username}.csv")
        if not os.path.exists(report_path):
            return []

        findings = []
        with open(report_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("exists", "").strip() == "Claimed":
                    findings.append({
                        "username": row.get("username", "").strip(),
                        "platform": row.get("name", "").strip(),
                        "url_main": row.get("url_main", "").strip(),
                        "url_user": row.get("url_user", "").strip(),
                        "http_status": row.get("http_status", "").strip(),
                        "error_reason": row.get("error_reason", "").strip(),
                    })

        return findings

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def run_maigret_async(username: str) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(run_maigret, username)