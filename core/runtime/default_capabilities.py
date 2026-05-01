from __future__ import annotations

import json
from typing import Any, Dict

from core.modules import list_modules, run_module
from core.videolm_client import (
    engine_demo_url,
    fetch_engine_health,
    fetch_engine_manifest,
    poll_notebooklm_video,
    resolve_video_url,
    submit_notebooklm_video,
)

from .capabilities import CapabilityContext, CapabilityRegistry, CapabilitySpec
from .policy import PolicyEngine


def build_default_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    @registry.register(
        CapabilitySpec(
            id="integration.videolm_health",
            name="VideoLM Health",
            description="Check the hosted VideoLM/Engine health endpoint.",
            category="integration",
            outputs_schema={"type": "object"},
            permissions_required=["network.read"],
            triggers_supported=["cli", "hub_command"],
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def videolm_health(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        return fetch_engine_health()

    @registry.register(
        CapabilitySpec(
            id="integration.videolm_manifest",
            name="VideoLM Manifest",
            description="Read the public VideoLM Engine manifest.",
            category="integration",
            outputs_schema={"type": "object"},
            permissions_required=["network.read"],
            triggers_supported=["cli", "hub_command"],
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def videolm_manifest(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        return fetch_engine_manifest()

    @registry.register(
        CapabilitySpec(
            id="integration.hosted_demo_url",
            name="Hosted Demo URL",
            description="Return the hosted HOMES-Engine reviewer demo URL.",
            category="integration",
            outputs_schema={"type": "object", "properties": {"url": {"type": "string"}}},
            permissions_required=[],
            triggers_supported=["cli", "hub_command"],
        )
    )
    def hosted_demo_url(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"url": engine_demo_url()}

    @registry.register(
        CapabilitySpec(
            id="production.notebooklm_submit",
            name="NotebookLM Video Submit",
            description="Submit a hosted NotebookLM video job through VideoLM.",
            category="production",
            inputs_schema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "title": {"type": "string"},
                    "theme": {"type": "string"},
                    "urls": {"type": "array", "items": {"type": "string"}},
                    "style": {"type": "string"},
                    "style_prompt": {"type": "string"},
                    "live_research": {"type": "boolean"},
                    "notebook_id": {"type": "string"},
                    "profile_id": {"type": "string"},
                },
            },
            outputs_schema={"type": "object"},
            permissions_required=["video.render", "network.write"],
            triggers_supported=["cli", "hub_job"],
            async_mode=True,
            writes_state=True,
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def notebooklm_submit(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        return submit_notebooklm_video(
            project_id=args.get("project_id", ""),
            title=args.get("title", ""),
            theme=args.get("theme", ""),
            urls=args.get("urls") or [],
            asset_paths=args.get("asset_paths") or [],
            style=args.get("style", "paper_craft"),
            style_prompt=args.get("style_prompt", ""),
            live_research=bool(args.get("live_research", False)),
            notebook_id=args.get("notebook_id", ""),
            profile_id=args.get("profile_id", "default"),
        )

    @registry.register(
        CapabilitySpec(
            id="production.notebooklm_poll",
            name="NotebookLM Video Poll",
            description="Poll a hosted NotebookLM video job and resolve its public MP4 URL.",
            category="production",
            inputs_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {"project_id": {"type": "string"}},
            },
            outputs_schema={"type": "object"},
            permissions_required=["network.read"],
            triggers_supported=["cli", "hub_command"],
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def notebooklm_poll(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args.get("project_id") or args.get("projectId")
        if not project_id:
            raise ValueError("project_id is required")
        result = poll_notebooklm_video(project_id)
        video_url = resolve_video_url(result.get("videoUrl") or result.get("videoPath") or "")
        if video_url:
            result["resolvedVideoUrl"] = video_url
        return result

    @registry.register(
        CapabilitySpec(
            id="agent.module_list",
            name="List Legacy Modules",
            description="List legacy module names available through core.modules.",
            category="agent",
            outputs_schema={"type": "object"},
            permissions_required=["profile.read"],
            triggers_supported=["cli", "hub_command"],
            experimental=True,
        )
    )
    def module_list(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"modules": list_modules()}

    @registry.register(
        CapabilitySpec(
            id="agent.module_run",
            name="Run Legacy Module",
            description="Run an existing core.modules entry behind the capability policy layer.",
            category="agent",
            inputs_schema={
                "type": "object",
                "required": ["module"],
                "properties": {
                    "module": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                },
            },
            outputs_schema={"type": "object"},
            permissions_required=["module.run"],
            triggers_supported=["cli", "hub_command"],
            writes_state=True,
            network_access=True,
            experimental=True,
        )
    )
    def module_run(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        module_name = args.get("module")
        if not module_name:
            raise ValueError("module is required")
        result = run_module(module_name, args.get("args") or [])
        return result or {"status": "error", "message": f"Module {module_name} returned no result"}

    return registry


def run_capability(
    capability_id: str,
    args: Dict[str, Any] | None = None,
    context: CapabilityContext | None = None,
    registry: CapabilityRegistry | None = None,
) -> Dict[str, Any]:
    registry = registry or build_default_registry()
    spec = registry.get(capability_id)
    profile = (context.profile if context else {}) or {}
    PolicyEngine(profile.get("policies") or {}).require(spec)
    return registry.run(capability_id, args or {}, context)


def parse_capability_args(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--capability-args must be a JSON object")
    return data
