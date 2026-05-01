from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional


CapabilityHandler = Callable[["CapabilityContext", Dict[str, Any]], Dict[str, Any]]


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    name: str
    description: str
    category: str
    inputs_schema: Dict[str, Any] = field(default_factory=dict)
    outputs_schema: Dict[str, Any] = field(default_factory=dict)
    permissions_required: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    triggers_supported: List[str] = field(default_factory=list)
    async_mode: bool = False
    writes_state: bool = False
    network_access: bool = False
    hardware_access: bool = False
    edge_compatible: bool = True
    hub_compatible: bool = True
    experimental: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityContext:
    profile: Dict[str, Any] = field(default_factory=dict)
    state: Any = None
    event: Optional[Dict[str, Any]] = None
    engine_id: str = "homes-engine"


class CapabilityRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, CapabilitySpec] = {}
        self._handlers: Dict[str, CapabilityHandler] = {}

    def register(self, spec: CapabilitySpec):
        if not spec.id:
            raise ValueError("Capability id is required")

        def decorator(handler: CapabilityHandler) -> CapabilityHandler:
            self._specs[spec.id] = spec
            self._handlers[spec.id] = handler
            return handler

        return decorator

    def add(self, spec: CapabilitySpec, handler: CapabilityHandler) -> None:
        self.register(spec)(handler)

    def get(self, capability_id: str) -> CapabilitySpec:
        if capability_id not in self._specs:
            raise KeyError(f"Unknown capability: {capability_id}")
        return self._specs[capability_id]

    def list(self, include_experimental: bool = False) -> List[Dict[str, Any]]:
        specs = self._specs.values()
        if not include_experimental:
            specs = [spec for spec in specs if not spec.experimental]
        return [spec.to_dict() for spec in sorted(specs, key=lambda spec: spec.id)]

    def run(
        self,
        capability_id: str,
        args: Optional[Dict[str, Any]] = None,
        context: Optional[CapabilityContext] = None,
    ) -> Dict[str, Any]:
        if capability_id not in self._handlers:
            raise KeyError(f"Unknown capability: {capability_id}")
        return self._handlers[capability_id](context or CapabilityContext(), args or {})
