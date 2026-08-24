"""
Given a set of typed inputs for one investigation, finds matching tools
via the registry and dispatches each as a Celery task. Returns immediately
with task/investigation info - callers poll each tool's own /status/{scan_id}
endpoint (Celery result isn't polled directly; scan_id already gives you
per-tool progress via the existing Scan table).
"""

import uuid
from dataclasses import dataclass

from app.celery_app import celery_app
from app.orchestrator.registry import tools_for_input


@dataclass
class InvestigationInput:
    file_path: str
    input_type: str  # "audio" | "video" | "image" | "username" | "email" | ...


def dispatch_investigation(target_label: str, inputs: list[InvestigationInput]) -> dict:
    investigation_id = uuid.uuid4()

    for inp in inputs:
        matched_tools = tools_for_input(inp.input_type)
        for tool in matched_tools:
            celery_app.send_task(
                tool.task_name,
                args=[target_label, inp.file_path, str(investigation_id)],
            )

    return {
        "investigation_id": str(investigation_id),
        "target_label": target_label,
    }