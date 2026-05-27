from __future__ import annotations

import json
import os
import platform
import shutil
import time
from pathlib import Path
from typing import Any, Dict

from core.video_maker import generate_video
from core.modules import list_modules, run_module
from core.videolm_client import (
    engine_demo_url,
    fetch_engine_health,
    fetch_engine_manifest,
    poll_factory_infographic_assets,
    poll_notebooklm_video,
    poll_studio_artifact,
    resolve_video_url,
    submit_factory_infographic_assets,
    submit_notebooklm_video,
    submit_studio_artifact,
)

from .capabilities import CapabilityContext, CapabilityRegistry, CapabilitySpec
from .events import record_event
from .manifest import build_runtime_manifest
from .policy import PolicyEngine
from .recipes import list_recipes, run_recipe


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
            id="agent.runtime_manifest",
            name="Runtime Manifest",
            description="Return the local HOMES-Engine capability, recipe, Hub, and profile manifest.",
            category="agent",
            outputs_schema={"type": "object"},
            permissions_required=["profile.read"],
            triggers_supported=["cli", "hub_command"],
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def runtime_manifest(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        manifest = build_runtime_manifest(
            registry,
            profile=context.profile,
            include_experimental=bool(args.get("include_experimental", True)),
        )
        if args.get("include_videolm", True):
            try:
                videolm_manifest = fetch_engine_manifest(timeout=int(args.get("videolm_timeout", 2)))
                artifact_types = videolm_manifest.get("artifactTypes") or videolm_manifest.get("artifact_types") or {}
                manifest["videolm"] = {
                    "baseUrl": videolm_manifest.get("baseUrl") or videolm_manifest.get("base_url"),
                    "capabilities": videolm_manifest.get("capabilities", {}),
                    "artifactTypes": artifact_types,
                    "artifact_types": artifact_types,
                }
                manifest["artifactTypes"] = artifact_types
                manifest["artifact_types"] = artifact_types
            except Exception as exc:
                manifest["videolm"] = {"status": "unavailable", "error": str(exc)}
        return manifest

    @registry.register(
        CapabilitySpec(
            id="agent.profile_summary",
            name="Profile Summary",
            description="Return profile preferences, configured sources, goals, devices, and policy permissions.",
            category="agent",
            outputs_schema={"type": "object"},
            permissions_required=["profile.read"],
            triggers_supported=["cli", "hub_command"],
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def profile_summary(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        profile = context.profile or {}
        return {
            "id": profile.get("id", "default"),
            "preferences": profile.get("preferences", {}),
            "goals": profile.get("goals", []),
            "devices": profile.get("devices", []),
            "policies": profile.get("policies", {}),
        }

    @registry.register(
        CapabilitySpec(
            id="agent.state_summary",
            name="State Summary",
            description="Return runtime state namespaces and recent event log entries.",
            category="agent",
            outputs_schema={"type": "object"},
            permissions_required=["state.read"],
            triggers_supported=["cli", "hub_command"],
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def state_summary(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        state = context.state
        if not state:
            return {"status": "unavailable", "namespaces": [], "recent_events": []}
        limit = int(args.get("limit", 10))
        return {
            "status": "available",
            "namespaces": state.namespaces(),
            "recent_events": state.recent_events(limit=limit),
        }

    @registry.register(
        CapabilitySpec(
            id="agent.output_list",
            name="Output List",
            description="List local render artifacts and remembered public outputs.",
            category="agent",
            outputs_schema={"type": "object"},
            permissions_required=["state.read"],
            triggers_supported=["cli", "hub_command"],
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def output_list(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(args.get("limit", 20))
        render_dir = Path(args.get("render_dir") or "output/renders")
        local_outputs = []
        if render_dir.exists():
            files = sorted(
                (path for path in render_dir.iterdir() if path.is_file()),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            for path in files[:limit]:
                stat = path.stat()
                local_outputs.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "size_bytes": stat.st_size,
                        "updated_at": stat.st_mtime,
                    }
                )
        remembered = context.state.list_namespace("outputs", limit=limit) if context.state else []
        return {"local_outputs": local_outputs, "remembered_outputs": remembered}

    @registry.register(
        CapabilitySpec(
            id="agent.output_remember",
            name="Remember Output",
            description="Persist a public or local artifact record in the runtime state store.",
            category="agent",
            inputs_schema={
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "url": {"type": "string"},
                    "path": {"type": "string"},
                    "type": {"type": "string"},
                    "metadata": {"type": "object"},
                },
            },
            outputs_schema={"type": "object"},
            permissions_required=["state.write"],
            triggers_supported=["cli", "hub_command", "recipe"],
            writes_state=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def output_remember(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        output_id = args.get("id")
        if not output_id:
            raise ValueError("id is required")
        if not context.state:
            raise RuntimeError("state store is unavailable")
        record = {
            "id": output_id,
            "url": args.get("url", ""),
            "path": args.get("path", ""),
            "type": args.get("type", "artifact"),
            "metadata": args.get("metadata") or {},
            "engine_id": context.engine_id,
            "created_at": time.time(),
        }
        context.state.set("outputs", output_id, record)
        record_event(context, "output.remembered", record)
        return {"status": "completed", "output": record}

    @registry.register(
        CapabilitySpec(
            id="agent.output_forget",
            name="Forget Output",
            description="Remove an artifact record from the runtime state store.",
            category="agent",
            inputs_schema={
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            },
            outputs_schema={"type": "object"},
            permissions_required=["state.write"],
            triggers_supported=["cli", "hub_command"],
            writes_state=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def output_forget(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        output_id = args.get("id")
        if not output_id:
            raise ValueError("id is required")
        if not context.state:
            raise RuntimeError("state store is unavailable")
        deleted = context.state.delete("outputs", output_id)
        record_event(context, "output.forgotten", {"id": output_id, "deleted": deleted})
        return {"status": "completed", "id": output_id, "deleted": deleted}

    @registry.register(
        CapabilitySpec(
            id="system.status",
            name="System Status",
            description="Return local platform, disk, memory, render directory, and Engine identity status.",
            category="perception",
            outputs_schema={"type": "object"},
            permissions_required=["system.read"],
            triggers_supported=["cli", "hub_command"],
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def system_status(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        usage = shutil.disk_usage(os.path.expanduser("~"))
        render_dir = Path(args.get("render_dir") or "output/renders")
        render_count = len([path for path in render_dir.iterdir() if path.is_file()]) if render_dir.exists() else 0
        status = {
            "engine_id": context.engine_id,
            "platform": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "disk": {
                "free_gb": round(usage.free / 1e9, 2),
                "total_gb": round(usage.total / 1e9, 2),
            },
            "renders": {
                "path": str(render_dir),
                "count": render_count,
            },
        }
        meminfo = _read_meminfo()
        if meminfo:
            status["memory"] = meminfo
        return status

    @registry.register(
        CapabilitySpec(
            id="production.video_render",
            name="Video Render",
            description="Render a public MP4 from a script file or inline script.",
            category="production",
            inputs_schema={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string"},
                    "script": {"type": "string"},
                    "topic": {"type": "string"},
                    "brand": {"type": "string"},
                    "theme": {"type": "string"},
                },
            },
            outputs_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "output_path": {"type": "string"},
                },
            },
            permissions_required=["video.render", "network.write", "state.write"],
            triggers_supported=["cli", "hub_job", "queue"],
            async_mode=True,
            writes_state=True,
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def video_render(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        script_path = args.get("script_path") or ""
        inline_script = args.get("script") or ""
        topic = args.get("topic") or "HOMES-Engine render"
        brand = args.get("brand") or args.get("theme") or "demo"

        if not script_path:
            os.makedirs("queue", exist_ok=True)
            script_path = os.path.join("queue", f"capability_{int(time.time())}.txt")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(inline_script.strip() or topic)

        record_event(context, "capability.started", {"id": "production.video_render", "script_path": script_path})
        output_path = generate_video(script_path, brand_name=brand)
        if not output_path:
            record_event(context, "capability.failed", {"id": "production.video_render", "script_path": script_path})
            return {"status": "error", "script_path": script_path, "output_path": ""}

        result = {"status": "completed", "script_path": script_path, "output_path": output_path}
        record_event(context, "capability.completed", {"id": "production.video_render", **result})
        return result

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
            format=args.get("format", "brief"),
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
            id="production.studio_artifact_submit",
            name="Studio Artifact Submit",
            description="Submit a generic VideoLM/NotebookLM Studio artifact job discovered from the Engine manifest.",
            category="production",
            inputs_schema={
                "type": "object",
                "required": ["project_id", "artifact_type"],
                "properties": {
                    "project_id": {"type": "string"},
                    "artifact_type": {"type": "string"},
                    "title": {"type": "string"},
                    "theme": {"type": "string"},
                    "urls": {"type": "array", "items": {"type": "string"}},
                    "asset_paths": {"type": "array", "items": {"type": "string"}},
                    "style": {"type": "string"},
                    "format": {"type": "string"},
                    "aspect": {"type": "string"},
                    "orientation": {"type": "string"},
                    "focus_prompt": {"type": "string"},
                    "focusPrompt": {"type": "string"},
                    "infographic_orientation": {"type": "string"},
                    "infographicOrientation": {"type": "string"},
                    "infographic_detail": {"type": "string"},
                    "infographicDetail": {"type": "string"},
                    "style_prompt": {"type": "string"},
                    "live_research": {"type": "boolean"},
                    "notebook_id": {"type": "string"},
                    "profile_id": {"type": "string"},
                },
            },
            outputs_schema={"type": "object"},
            permissions_required=["artifact.create", "network.write", "state.write"],
            triggers_supported=["cli", "hub_job", "hub_command"],
            async_mode=True,
            writes_state=True,
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def studio_artifact_submit(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args.get("project_id") or args.get("projectId")
        artifact_type = args.get("artifact_type") or args.get("artifactType") or args.get("type") or "video"
        if not project_id:
            raise ValueError("project_id is required")
        result = submit_studio_artifact(
            project_id=project_id,
            artifact_type=artifact_type,
            title=args.get("title", ""),
            theme=args.get("theme", ""),
            urls=args.get("urls") or [],
            asset_paths=args.get("asset_paths") or args.get("assets") or [],
            style=args.get("style", "paper_craft"),
            format=args.get("format", "brief"),
            aspect=args.get("aspect", ""),
            focus_prompt=args.get("focus_prompt") or args.get("focusPrompt", ""),
            infographic_orientation=args.get("infographic_orientation") or args.get("infographicOrientation") or args.get("orientation", ""),
            infographic_detail=args.get("infographic_detail") or args.get("infographicDetail", ""),
            style_prompt=args.get("style_prompt") or args.get("stylePrompt", ""),
            live_research=bool(args.get("live_research", args.get("liveResearch", False))),
            notebook_id=args.get("notebook_id") or args.get("notebookId", ""),
            profile_id=args.get("profile_id") or args.get("profileId", "default"),
        )
        record_event(context, "artifact.submitted", {"project_id": project_id, "artifact_type": artifact_type, "result": result})
        return result

    @registry.register(
        CapabilitySpec(
            id="production.studio_artifact_poll",
            name="Studio Artifact Poll",
            description="Poll a generic VideoLM/NotebookLM Studio artifact and normalize its final URL.",
            category="production",
            inputs_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "artifact_type": {"type": "string"},
                },
            },
            outputs_schema={"type": "object"},
            permissions_required=["network.read"],
            triggers_supported=["cli", "hub_command"],
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def studio_artifact_poll(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args.get("project_id") or args.get("projectId")
        if not project_id:
            raise ValueError("project_id is required")
        return poll_studio_artifact(
            project_id,
            artifact_type=args.get("artifact_type") or args.get("artifactType", ""),
        )

    @registry.register(
        CapabilitySpec(
            id="production.factory_infographic_assets_submit",
            name="Factory Infographic Assets Submit",
            description="Start VideoLM Factory infographic asset generation for storyboard scenes.",
            category="production",
            inputs_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "theme": {"type": "string"},
                    "urls": {"type": "array", "items": {"type": "string"}},
                    "style": {"type": "string"},
                    "aspect": {"type": "string"},
                    "orientation": {"type": "string"},
                    "notebook_id": {"type": "string"},
                    "profile_id": {"type": "string"},
                },
            },
            outputs_schema={"type": "object"},
            permissions_required=["artifact.create", "network.write", "state.write"],
            triggers_supported=["cli", "hub_job", "hub_command"],
            async_mode=True,
            writes_state=True,
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def factory_infographic_assets_submit(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args.get("project_id") or args.get("projectId")
        if not project_id:
            raise ValueError("project_id is required")
        result = submit_factory_infographic_assets(
            project_id=project_id,
            theme=args.get("theme", ""),
            urls=args.get("urls") or [],
            style=args.get("style", "paper_craft"),
            aspect=args.get("aspect", "portrait"),
            orientation=args.get("orientation", ""),
            notebook_id=args.get("notebook_id") or args.get("notebookId", ""),
            profile_id=args.get("profile_id") or args.get("profileId", "default"),
        )
        record_event(context, "artifact.factory_infographic_assets.submitted", {"project_id": project_id, "result": result})
        return result

    @registry.register(
        CapabilitySpec(
            id="production.factory_infographic_assets_poll",
            name="Factory Infographic Assets Poll",
            description="Poll a VideoLM Factory infographic asset generation job.",
            category="production",
            inputs_schema={
                "type": "object",
                "required": ["job_id"],
                "properties": {"job_id": {"type": "string"}},
            },
            outputs_schema={"type": "object"},
            permissions_required=["network.read"],
            triggers_supported=["cli", "hub_command"],
            network_access=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def factory_infographic_assets_poll(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        job_id = args.get("job_id") or args.get("jobId")
        if not job_id:
            raise ValueError("job_id is required")
        return poll_factory_infographic_assets(job_id)

    @registry.register(
        CapabilitySpec(
            id="agent.recipe_list",
            name="List Recipes",
            description="List available multi-step capability recipes.",
            category="agent",
            outputs_schema={"type": "object"},
            permissions_required=["profile.read"],
            triggers_supported=["cli", "hub_command"],
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def recipe_list(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"recipes": list_recipes(args.get("root", "recipes"))}

    @registry.register(
        CapabilitySpec(
            id="agent.recipe_run",
            name="Run Recipe",
            description="Run a declarative multi-step capability recipe.",
            category="agent",
            inputs_schema={
                "type": "object",
                "required": ["recipe_id"],
                "properties": {
                    "recipe_id": {"type": "string"},
                    "inputs": {"type": "object"},
                },
            },
            outputs_schema={"type": "object"},
            permissions_required=["recipe.run", "state.write"],
            triggers_supported=["cli", "hub_command"],
            writes_state=True,
            edge_compatible=True,
            hub_compatible=True,
        )
    )
    def recipe_run(context: CapabilityContext, args: Dict[str, Any]) -> Dict[str, Any]:
        recipe_id = args.get("recipe_id") or args.get("id")
        if not recipe_id:
            raise ValueError("recipe_id is required")
        return run_recipe(recipe_id, inputs=args.get("inputs") or {}, context=context, root=args.get("root", "recipes"))

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
    active_context = context or CapabilityContext(profile=profile)
    record_event(active_context, "capability.invoked", {"id": capability_id, "args": args or {}})
    return registry.run(capability_id, args or {}, active_context)


def parse_capability_args(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--capability-args must be a JSON object")
    return data


def _read_meminfo() -> Dict[str, Any]:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return {}
    values = {}
    for line in lines:
        key, raw_value = line.split(":", 1)
        values[key] = int(raw_value.strip().split()[0])
    total_mb = values.get("MemTotal", 0) // 1024
    available_mb = values.get("MemAvailable", 0) // 1024
    if not total_mb:
        return {}
    return {
        "total_mb": total_mb,
        "available_mb": available_mb,
        "used_mb": total_mb - available_mb,
    }
