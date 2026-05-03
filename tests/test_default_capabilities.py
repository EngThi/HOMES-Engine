import pytest

from core.runtime import CapabilityContext, load_profile
from core.runtime import StateStore
from core.runtime import default_capabilities
from core.runtime.default_capabilities import build_default_registry, parse_capability_args, run_capability


def test_default_registry_lists_production_capabilities_without_experimental():
    registry = build_default_registry()
    ids = {item["id"] for item in registry.list()}

    assert "agent.output_list" in ids
    assert "agent.output_forget" in ids
    assert "agent.profile_summary" in ids
    assert "agent.runtime_manifest" in ids
    assert "agent.state_summary" in ids
    assert "integration.hosted_demo_url" in ids
    assert "integration.videolm_health" in ids
    assert "production.video_render" in ids
    assert "production.notebooklm_poll" in ids
    assert "production.studio_artifact_submit" in ids
    assert "production.studio_artifact_poll" in ids
    assert "production.factory_infographic_assets_submit" in ids
    assert "production.factory_infographic_assets_poll" in ids
    assert "system.status" in ids
    assert "agent.module_run" not in ids


def test_default_registry_lists_experimental_when_requested():
    registry = build_default_registry()
    ids = {item["id"] for item in registry.list(include_experimental=True)}

    assert "agent.module_list" in ids
    assert "agent.module_run" in ids


def test_run_capability_uses_policy_from_profile():
    profile = load_profile("default")
    context = CapabilityContext(profile=profile)

    result = run_capability("integration.hosted_demo_url", context=context)

    assert result["url"].endswith("/engine-demo")


def test_runtime_manifest_capability_includes_recipes():
    profile = load_profile("default")
    context = CapabilityContext(profile=profile)

    result = run_capability("agent.runtime_manifest", context=context)

    assert result["name"] == "HOMES-Engine"
    assert result["capabilities_count"] >= 1
    assert any(item["id"] == "engine_smoke" for item in result["recipes"])


def test_profile_summary_uses_runtime_profile():
    profile = load_profile("default")
    context = CapabilityContext(profile=profile)

    result = run_capability("agent.profile_summary", context=context)

    assert result["id"] == "default"
    assert "policies" in result


def test_state_summary_reads_state_store(tmp_path):
    state = StateStore(str(tmp_path / "state.sqlite"))
    state.set("outputs", "video1", {"url": "https://example.com/video.mp4"})
    state.append_event("demo.event", {"ok": True})
    context = CapabilityContext(profile=load_profile("default"), state=state)

    result = run_capability("agent.state_summary", {"limit": 1}, context=context)

    assert result["status"] == "available"
    assert "outputs" in result["namespaces"]
    assert result["recent_events"][0]["event_type"] == "capability.invoked"


def test_output_remember_and_list(tmp_path):
    state = StateStore(str(tmp_path / "state.sqlite"))
    context = CapabilityContext(profile=load_profile("default"), state=state, engine_id="engine-test")

    remembered = run_capability(
        "agent.output_remember",
        {"id": "video1", "url": "https://example.com/video.mp4", "type": "video"},
        context=context,
    )
    listed = run_capability("agent.output_list", {"render_dir": str(tmp_path / "renders")}, context=context)

    assert remembered["status"] == "completed"
    assert listed["remembered_outputs"][0]["key"] == "video1"
    assert listed["remembered_outputs"][0]["value"]["engine_id"] == "engine-test"


def test_output_forget_removes_remembered_output(tmp_path):
    state = StateStore(str(tmp_path / "state.sqlite"))
    context = CapabilityContext(profile=load_profile("default"), state=state)
    run_capability("agent.output_remember", {"id": "video1", "url": "https://example.com/video.mp4"}, context=context)

    result = run_capability("agent.output_forget", {"id": "video1"}, context=context)

    assert result == {"status": "completed", "id": "video1", "deleted": True}
    assert state.list_namespace("outputs") == []


def test_system_status_returns_machine_info(tmp_path):
    context = CapabilityContext(profile=load_profile("default"), state=StateStore(str(tmp_path / "state.sqlite")))

    result = run_capability("system.status", {"render_dir": str(tmp_path / "renders")}, context=context)

    assert result["engine_id"] == "homes-engine"
    assert result["disk"]["total_gb"] > 0
    assert result["renders"]["count"] == 0


def test_run_capability_blocks_missing_permission():
    profile = load_profile("default")
    context = CapabilityContext(profile=profile)

    with pytest.raises(PermissionError):
        run_capability("agent.module_run", {"module": "skill_tree"}, context=context)


def test_parse_capability_args_requires_object():
    assert parse_capability_args('{"project_id":"demo"}') == {"project_id": "demo"}

    with pytest.raises(ValueError):
        parse_capability_args('["not", "object"]')


def test_video_render_capability_uses_existing_renderer(monkeypatch, tmp_path):
    script_path = tmp_path / "script.txt"
    script_path.write_text("hello", encoding="utf-8")
    state = StateStore(str(tmp_path / "state.sqlite"))
    context = CapabilityContext(profile=load_profile("default"), state=state)

    monkeypatch.setattr(default_capabilities, "generate_video", lambda path, brand_name="demo": "output/renders/demo.mp4")

    result = run_capability(
        "production.video_render",
        {"script_path": str(script_path), "brand": "demo"},
        context=context,
    )

    assert result["status"] == "completed"
    assert result["output_path"] == "output/renders/demo.mp4"
    assert state.recent_events()[0]["event_type"] == "capability.completed"


def test_studio_artifact_submit_capability(monkeypatch, tmp_path):
    state = StateStore(str(tmp_path / "state.sqlite"))
    context = CapabilityContext(profile=load_profile("default"), state=state)
    monkeypatch.setattr(
        default_capabilities,
        "submit_studio_artifact",
        lambda **kwargs: {"status": "submitted", "artifact_type": kwargs["artifact_type"]},
    )

    result = run_capability(
        "production.studio_artifact_submit",
        {"project_id": "studio1", "artifact_type": "infographic"},
        context=context,
    )

    assert result == {"status": "submitted", "artifact_type": "infographic"}


def test_studio_artifact_poll_capability(monkeypatch):
    context = CapabilityContext(profile=load_profile("default"))
    monkeypatch.setattr(
        default_capabilities,
        "poll_studio_artifact",
        lambda project_id, artifact_type="": {"status": "completed", "project_id": project_id, "artifact_type": artifact_type},
    )

    result = run_capability(
        "production.studio_artifact_poll",
        {"project_id": "studio1", "artifact_type": "infographic"},
        context=context,
    )

    assert result["status"] == "completed"
    assert result["artifact_type"] == "infographic"
