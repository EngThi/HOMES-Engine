from core.runtime import CapabilityContext, StateStore, load_profile
from core.runtime import recipes


def test_list_recipes_reads_recipe_files():
    found = {recipe["id"] for recipe in recipes.list_recipes()}

    assert "engine_smoke" in found
    assert "video_render_demo" in found


def test_run_recipe_executes_steps_with_templates(monkeypatch, tmp_path):
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    (recipe_dir / "demo.json").write_text(
        """
        {
          "id": "demo",
          "steps": [
            {"id": "first", "capability": "cap.echo", "args": {"value": "{{inputs.topic}}"}},
            {"id": "second", "capability": "cap.echo", "args": {"value": "{{steps.first.value}}"}}
          ]
        }
        """,
        encoding="utf-8",
    )
    calls = []

    def fake_run_capability(capability_id, args=None, context=None):
        calls.append((capability_id, args))
        return {"status": "completed", "value": args["value"]}

    context = CapabilityContext(profile=load_profile("default"), state=StateStore(str(tmp_path / "state.sqlite")))

    result = recipes.run_recipe(
        "demo",
        {"topic": "HOMES"},
        context=context,
        root=str(recipe_dir),
        executor=fake_run_capability,
    )

    assert result["status"] == "completed"
    assert calls == [
        ("cap.echo", {"value": "HOMES"}),
        ("cap.echo", {"value": "HOMES"}),
    ]
    assert context.state.recent_events()[0]["event_type"] == "recipe.completed"
