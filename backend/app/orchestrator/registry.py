"""
Discovers every tool under app/tools/<name>/ that has declared itself
orchestrator-ready: ACCEPTED_INPUTS (in service.py) + a Celery task
named "<tool_id>.run" (in tasks.py). Tools missing either are skipped -
they still work standalone via their own router/HTTP endpoint.
"""

import importlib
import pkgutil
from dataclasses import dataclass

import app.tools as tools_pkg
from app.celery_app import celery_app


@dataclass
class OrchestratorTool:
    tool_id: str
    accepted_inputs: set[str]
    task_name: str  # celery task name, used via celery_app.send_task


def discover_orchestrator_tools() -> list[OrchestratorTool]:
    discovered: list[OrchestratorTool] = []

    for _, tool_name, is_pkg in pkgutil.iter_modules(tools_pkg.__path__):
        if not is_pkg:
            continue

        service_module_path = f"app.tools.{tool_name}.service"
        try:
            service_module = importlib.import_module(service_module_path)
        except ModuleNotFoundError:
            continue

        if not hasattr(service_module, "ACCEPTED_INPUTS"):
            continue

        tasks_module_path = f"app.tools.{tool_name}.tasks"
        try:
            importlib.import_module(tasks_module_path)
        except ModuleNotFoundError:
            continue  # tasks.py doesn't exist yet for this tool

        task_name = f"{service_module.TOOL_ID}.run"
        if task_name not in celery_app.tasks:
            continue

        discovered.append(
            OrchestratorTool(
                tool_id=service_module.TOOL_ID,
                accepted_inputs=service_module.ACCEPTED_INPUTS,
                task_name=task_name,
            )
        )

    return discovered


def tools_for_input(input_type: str) -> list[OrchestratorTool]:
    return [t for t in discover_orchestrator_tools() if input_type in t.accepted_inputs]