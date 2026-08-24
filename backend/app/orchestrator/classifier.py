"""
Classifier node: only runs for inputs whose type couldn't be determined
deterministically (unrecognized file extension, or free-text input that
isn't obviously a known shape). Uses local llama3.1 via Ollama to guess
the input type, logs the decision unconditionally to ClassificationLog
for later manual like/dislike review (feedback stays NULL until reviewed).
"""

import json

from langchain_ollama import ChatOllama

from app.db.postgres import SessionLocal
from app.models.classification_log import ClassificationLog
from app.orchestrator.registry import discover_orchestrator_tools

llm = ChatOllama(model="llama3.1", temperature=0, base_url="http://127.0.0.1:11434")

KNOWN_TYPES = ["audio", "video", "image", "username", "email", "text", "unknown"]


def classify_input(description: str) -> str:
    """
    description: something short and safe to hand the LLM - e.g. a
    filename + extension, or a raw text snippet if it's a bare string
    input. Never pass full file contents here.
    """
    prompt = f"""You are classifying an OSINT investigation input.
Given this input description, respond with ONLY one word from this list: {KNOWN_TYPES}

Input: {description}

Answer with exactly one word, nothing else."""

    response = llm.invoke(prompt)
    guess = response.content.strip().lower()

    if guess not in KNOWN_TYPES:
        guess = "unknown"

    return guess


def classify_and_log(investigation_id: str, description: str) -> str:
    guess = classify_input(description)

    matched_tools = [
        t.tool_id for t in discover_orchestrator_tools()
        if guess in t.accepted_inputs
    ]

    db = SessionLocal()
    try:
        log = ClassificationLog(
            investigation_id=investigation_id,
            input_description=description,
            suggested_tools=matched_tools,
            confidence=None,  # ChatOllama doesn't return a confidence score natively
        )
        db.add(log)
        db.commit()
    finally:
        db.close()

    return guess