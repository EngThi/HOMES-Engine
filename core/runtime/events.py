from __future__ import annotations

from typing import Any, Dict


def record_event(context: Any, event_type: str, payload: Dict[str, Any]) -> None:
    state = getattr(context, "state", None)
    if not state:
        return
    append_event = getattr(state, "append_event", None)
    if not append_event:
        return
    append_event(event_type, payload)
