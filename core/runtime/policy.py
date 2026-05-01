from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from .capabilities import CapabilitySpec


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str = ""


class PolicyEngine:
    """Small allowlist-based policy layer for capability execution."""

    def __init__(self, policy: Dict | None = None) -> None:
        self.policy = policy or {}

    def decide(self, spec: CapabilitySpec) -> PolicyDecision:
        denied = set(self.policy.get("deny_permissions", []))
        allowed = set(self.policy.get("allow_permissions", []))
        required = set(spec.permissions_required)

        blocked = sorted(required & denied)
        if blocked:
            return PolicyDecision(False, f"Denied permissions: {', '.join(blocked)}")

        if required and allowed and not required.issubset(allowed):
            missing = sorted(required - allowed)
            return PolicyDecision(False, f"Missing allowed permissions: {', '.join(missing)}")

        if spec.hardware_access and not self.policy.get("allow_hardware", False):
            return PolicyDecision(False, "Hardware access is not allowed")

        if spec.network_access and self.policy.get("network", "allow") == "deny":
            return PolicyDecision(False, "Network access is denied")

        return PolicyDecision(True, "allowed")

    def require(self, spec: CapabilitySpec) -> None:
        decision = self.decide(spec)
        if not decision.allowed:
            raise PermissionError(decision.reason)


def policy_from_permissions(permissions: Iterable[str]) -> PolicyEngine:
    return PolicyEngine({"allow_permissions": list(permissions)})
