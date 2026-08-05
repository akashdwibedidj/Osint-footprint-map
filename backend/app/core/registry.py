"""
Auto-discovers every tool under app/tools/<name>/router.py and mounts
its APIRouter onto the FastAPI app. This is the piece that lets you
add a new OSINT tool by dropping in a new folder -- main.py itself
never changes again.

Contract each app/tools/<name>/router.py must satisfy:
    TOOL_ID: str
    router: fastapi.APIRouter
"""

import importlib
import pkgutil
from dataclasses import dataclass

from fastapi import FastAPI

import app.tools as tools_pkg


@dataclass
class RegisteredTool:
    tool_id: str
    module: str


def discover_tools() -> list[RegisteredTool]:
    registered: list[RegisteredTool] = []

    for _, tool_name, is_pkg in pkgutil.iter_modules(tools_pkg.__path__):
        if not is_pkg:
            continue

        router_module_path = f"app.tools.{tool_name}.router"
        try:
            router_module = importlib.import_module(router_module_path)
        except ModuleNotFoundError:
            # Tool folder without a router.py yet (e.g. mid-development) -- skip it.
            continue

        if not hasattr(router_module, "router"):
            raise RuntimeError(
                f"app.tools.{tool_name}.router must define a `router` (APIRouter)"
            )
        if not hasattr(router_module, "TOOL_ID"):
            raise RuntimeError(
                f"app.tools.{tool_name}.router must define a `TOOL_ID` string"
            )

        registered.append(RegisteredTool(tool_id=router_module.TOOL_ID, module=router_module_path))

    return registered


def register_tools(app: FastAPI) -> list[RegisteredTool]:
    registered = discover_tools()
    for tool in registered:
        router_module = importlib.import_module(tool.module)
        app.include_router(router_module.router)
    return registered
