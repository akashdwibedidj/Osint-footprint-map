"""
LangGraph definition. Two nodes:
  1. route_inputs  - deterministic type detection for known extensions;
                      falls back to classify_and_log for anything unrecognized.
  2. dispatch       - sends a Celery task per matched tool per input.
Linear graph for now (route -> dispatch -> end) - branching complexity
isn't needed yet since there's no multi-step reasoning happening between
nodes, just two sequential jobs.
"""

import os

from langgraph.graph import StateGraph, END

from app.celery_app import celery_app
from app.orchestrator.classifier import classify_and_log
from app.orchestrator.registry import tools_for_input
from app.orchestrator.state import InvestigationState

EXTENSION_TYPE_MAP = {
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".ogg": "audio",
    ".mp4": "video", ".mov": "video", ".mkv": "video", ".avi": "video",
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image",
}


def _detect_from_extension(file_path: str) -> str | None:
    ext = os.path.splitext(file_path)[1].lower()
    return EXTENSION_TYPE_MAP.get(ext)


def route_inputs(state: InvestigationState) -> InvestigationState:
    for item in state["inputs"]:
        if item["input_type"]:
            continue  # already typed explicitly by the frontend

        if item["file_path"]:
            detected = _detect_from_extension(item["file_path"])
            if detected:
                item["input_type"] = detected
                continue
            description = os.path.basename(item["file_path"])
        else:
            description = item["raw_text"] or ""
            # a bare raw_text input with no file - if the frontend already
            # tagged it as "username" via input_type, we'd have skipped above.
            # Only reaches here if truly untyped free text - falls through
            # to the classifier below.

        guess = classify_and_log(state["investigation_id"], description)
        item["input_type"] = guess

    return state


def dispatch(state: InvestigationState) -> InvestigationState:
    dispatched = []
    for item in state["inputs"]:
        if not item["input_type"] or item["input_type"] == "unknown":
            continue

        matched_tools = tools_for_input(item["input_type"])
        for tool in matched_tools:
            if item["input_type"] == "username":
                # username-based tools take raw_text, not file_path
                args = [state["target_label"], item["raw_text"], state["investigation_id"]]
            else:
                args = [state["target_label"], item["file_path"], state["investigation_id"]]

            celery_app.send_task(tool.task_name, args=args)
            dispatched.append({"tool_id": tool.tool_id, "task_name": tool.task_name})

    state["dispatched"] = dispatched
    return state


def build_graph():
    graph = StateGraph(InvestigationState)
    graph.add_node("route_inputs", route_inputs)
    graph.add_node("dispatch", dispatch)
    graph.set_entry_point("route_inputs")
    graph.add_edge("route_inputs", "dispatch")
    graph.add_edge("dispatch", END)
    return graph.compile()


investigation_graph = build_graph()