# backend/state.py
import uuid
from typing import Any, Dict

# In-memory store for now
_store: Dict[str, Dict[str, Any]] = {}

def new_session(raw_data: Any) -> str:
    """
    Create a new session, store raw telemetry, and return a session_id.
    """
    session_id = str(uuid.uuid4())
    _store[session_id] = {
        "raw": raw_data,      # full telemetry JSON
        "history": []         # chat history
    }
    return session_id

def get_session(session_id: str) -> Dict[str, Any]:
    """
    Retrieve session data by ID (or None if not found).
    """
    return _store.get(session_id)
