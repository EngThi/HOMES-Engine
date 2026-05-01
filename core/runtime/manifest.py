from __future__ import annotations

import os
import platform
from typing import Any, Dict

from .recipes import list_recipes


def build_runtime_manifest(
    registry: Any,
    profile: Dict[str, Any] | None = None,
    include_experimental: bool = True,
) -> Dict[str, Any]:
    profile = profile or {}
    policies = profile.get("policies") or {}
    capabilities = registry.list(include_experimental=include_experimental)
    return {
        "name": "HOMES-Engine",
        "kind": "modular_personal_runtime",
        "version": "0.4.0",
        "engine_id": os.getenv("ENGINE_ID", "homes-engine"),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "hub": {
            "url": os.getenv("HOMES_HUB_URL", ""),
            "commands": [
                "run_capability",
                "run_recipe",
                "generate_video",
                "status",
            ],
            "signed_posts": [
                "/api/projects/:id/status",
                "/api/projects/:id/complete",
                "/api/sensors",
            ],
        },
        "capabilities": capabilities,
        "capabilities_count": len(capabilities),
        "recipes": list_recipes(),
        "profile": {
            "id": profile.get("id", "default"),
            "allow_permissions": policies.get("allow_permissions", []),
            "deny_permissions": policies.get("deny_permissions", []),
        },
    }
