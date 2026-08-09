import asyncio
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from app.core.tool_base import NormalizedFinding
from app.models.finding import ExposureCategory

GITLEAKS_BIN = "gitleaks"  # must be on PATH (see Dockerfile note)
CLONE_TIMEOUT_S = 60
SCAN_TIMEOUT_S = 120


def _normalize_repo_url(target_value: str) -> str:
    """
    Accepts either a full git URL, or a bare 'owner/repo' shorthand,
    and returns a cloneable https URL.
    """
    value = target_value.strip()
    if value.startswith("http://") or value.startswith("https://") or value.endswith(".git"):
        return value
    # owner/repo shorthand -> github https clone url
    return f"https://github.com/{value}.git"


def _run_subprocess_blocking(args: tuple[str, ...], timeout: int) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Command timed out after {timeout}s: {' '.join(args)}")
    return (
        result.returncode,
        result.stdout.decode(errors="replace"),
        result.stderr.decode(errors="replace"),
    )


async def _run_subprocess(*args: str, timeout: int) -> tuple[int, str, str]:
    # asyncio.create_subprocess_exec requires ProactorEventLoop on Windows and
    # raises a bare NotImplementedError under SelectorEventLoop (common when
    # other libs force selector mode). Running the blocking call in a thread
    # sidesteps that entirely and works the same on every OS.
    return await asyncio.to_thread(_run_subprocess_blocking, args, timeout)


async def _clone_repo(repo_url: str, dest_dir: str) -> None:
    returncode, _, stderr = await _run_subprocess(
        "git", "clone", "--depth", "1", "--single-branch", repo_url, dest_dir,
        timeout=CLONE_TIMEOUT_S,
    )
    if returncode != 0:
        raise RuntimeError(f"git clone failed: {stderr.strip()}")


async def _run_gitleaks(repo_dir: str, report_path: str) -> None:
    # exit code 1 from gitleaks means "leaks found", not an error -- only treat
    # unexpected codes (>1) or missing report as real failures.
    returncode, _, stderr = await _run_subprocess(
        GITLEAKS_BIN, "detect",
        "--source", repo_dir,
        "--report-format", "json",
        "--report-path", report_path,
        "--redact",  # redact secret values in the output report
        "--exit-code", "1",
        timeout=SCAN_TIMEOUT_S,
    )
    if returncode not in (0, 1):
        raise RuntimeError(f"gitleaks scan failed: {stderr.strip()}")


def _load_report(report_path: str) -> list[dict]:
    path = Path(report_path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    with open(path, "r") as f:
        return json.load(f)


def _severity_for_rule(rule_id: str) -> str:
    high_risk_markers = ("private-key", "aws", "gcp", "azure", "stripe", "slack", "github-pat", "generic-api-key")
    rule_lower = (rule_id or "").lower()
    if any(marker in rule_lower for marker in high_risk_markers):
        return "high"
    return "medium"


async def run(
    target_value: str,
    **kwargs,
) -> list[NormalizedFinding]:
    """
    target_value: a git repo URL, or 'owner/repo' shorthand (GitHub assumed).
    """
    repo_url = _normalize_repo_url(target_value)
    tmp_dir = tempfile.mkdtemp(prefix="gitleak_scan_")
    report_path = str(Path(tmp_dir) / "report.json")

    findings: list[NormalizedFinding] = []
    start = time.monotonic()

    try:
        repo_dir = str(Path(tmp_dir) / "repo")
        await _clone_repo(repo_url, repo_dir)
        await _run_gitleaks(repo_dir, report_path)
        leaks = _load_report(report_path)
        elapsed = time.monotonic() - start

        for leak in leaks:
            rule_id = leak.get("RuleID", "unknown_rule")
            file_path = leak.get("File", "unknown_file")
            line_start = leak.get("StartLine")
            commit = leak.get("Commit")
            author = leak.get("Author")
            email = leak.get("Email")
            date = leak.get("Date")
            secret_redacted = leak.get("Secret", "")  # already redacted by --redact flag

            findings.append(
                NormalizedFinding(
                    source="gitleak_scanner",
                    source_url=repo_url,
                    raw_value=f"{rule_id} in {file_path}:{line_start}",
                    category=ExposureCategory.CREDENTIAL,
                    response_time_s=elapsed,
                    extra_metadata={
                        "rule_id": rule_id,
                        "file": file_path,
                        "line_start": line_start,
                        "commit": commit,
                        "author": author,
                        "author_email": email,
                        "commit_date": date,
                        "secret_redacted": secret_redacted,
                        "severity_hint": _severity_for_rule(rule_id),
                    },
                )
            )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return findings