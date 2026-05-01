import pytest

from core.runtime import CapabilityContext, load_profile
from core.runtime import StateStore
from core.runtime import default_capabilities
from core.runtime.default_capabilities import build_default_registry, parse_capability_args, run_capability


def test_default_registry_lists_production_capabilities_without_experimental():
    registry = build_default_registry()
    ids = {item["id"] for item in registry.list()}

    assert "integration.hosted_demo_url" in ids
    assert "integration.videolm_health" in ids
    assert "production.video_render" in ids
    assert "production.notebooklm_poll" in ids
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
