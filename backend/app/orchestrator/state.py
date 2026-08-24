"""
The state object passed between LangGraph nodes for one investigation run.
TypedDict, not a dataclass - LangGraph expects state as a dict-like object
it can merge updates into between nodes.
"""

from typing import TypedDict
import uuid


class InputItem(TypedDict):
    file_path: str
    raw_text: str | None       # set instead of file_path for username/email/text inputs
    input_type: str | None     # "audio" | "video" | "image" | "username" | "email" | None if undetected


class DispatchRecord(TypedDict):
    tool_id: str
    task_name: str


class InvestigationState(TypedDict):
    investigation_id: str
    target_label: str
    inputs: list[InputItem]
    dispatched: list[DispatchRecord]