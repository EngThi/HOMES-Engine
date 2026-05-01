from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_PROFILE: Dict[str, Any] = {
    "id": "default",
    "name": "Default HOMES profile",
    "preferences": {
        "language": "en-US",
        "timezone": "UTC",
        "video_style": "terminal-first technical demo",
        "rss_feeds": ["https://hnrss.org/frontpage"],
    },
    "goals": [],
    "devices": [],
    "sources": [],
    "policies": {
        "network": "allow",
        "allow_hardware": False,
        "allow_permissions": [
            "video.render",
            "hub.report",
            "profile.read",
            "state.write",
            "network.read",
            "network.write",
        ],
        "deny_permissions": [],
    },
}


def load_profile(name: str = "default", root: str = "profiles") -> Dict[str, Any]:
    """Load a user profile without hardcoding personal context in modules."""
    profile_path = Path(root) / f"{name}.json"
    legacy_path = Path("profile.json")

    if profile_path.exists():
        return _merge(DEFAULT_PROFILE, _load_json(profile_path))
    if name == "default" and legacy_path.exists():
        return _merge(DEFAULT_PROFILE, _load_json(legacy_path))
    return dict(DEFAULT_PROFILE)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result
