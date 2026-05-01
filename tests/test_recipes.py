from core.runtime import CapabilityContext, StateStore, load_profile
from core.runtime import recipes


def test_list_recipes_reads_recipe_files():
    found = {recipe["id"]: recipe for recipe in recipes.list_recipes()}

    assert "engine_smoke" in found
    assert "video_render_demo" in found
    assert found["video_render_demo"]["required_inputs"] == ["topic", "script"]


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


def test_run_recipe_applies_input_defaults(tmp_path):
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    (recipe_dir / "demo.json").write_text(
        """
        {
          "id": "demo",
          "input_defaults": {"brand": "demo"},
          "steps": [
            {"id": "first", "capability": "cap.echo", "args": {"brand": "{{inputs.brand}}"}}
          ]
        }
        """,
        encoding="utf-8",
    )
    calls = []

    def fake_run_capability(capability_id, args=None, context=None):
        calls.append((capability_id, args))
        return {"status": "completed"}

    result = recipes.run_recipe("demo", {}, root=str(recipe_dir), executor=fake_run_capability)

    assert result["status"] == "completed"
    assert calls == [("cap.echo", {"brand": "demo"})]


def test_run_recipe_requires_declared_inputs(tmp_path):
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    (recipe_dir / "demo.json").write_text(
        """
        {
          "id": "demo",
          "required_inputs": ["topic"],
          "steps": [{"id": "first", "capability": "cap.echo", "args": {}}]
        }
        """,
        encoding="utf-8",
    )

    try:
        recipes.run_recipe("demo", {}, root=str(recipe_dir), executor=lambda *args, **kwargs: {})
    except ValueError as e:
        assert "missing required inputs: topic" in str(e)
    else:
        raise AssertionError("Expected missing required input error")


def test_run_recipe_stops_on_error_status(tmp_path):
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    (recipe_dir / "demo.json").write_text(
        """
        {
          "id": "demo",
          "steps": [
            {"id": "first", "capability": "cap.fail", "args": {}},
            {"id": "second", "capability": "cap.echo", "args": {}}
          ]
        }
        """,
        encoding="utf-8",
    )
    calls = []

    def fake_run_capability(capability_id, args=None, context=None):
        calls.append(capability_id)
        return {"status": "error"}

    result = recipes.run_recipe("demo", {}, root=str(recipe_dir), executor=fake_run_capability)

    assert result["status"] == "error"
    assert result["failed_step"] == "first"
    assert calls == ["cap.fail"]


def test_run_recipe_can_continue_on_error(tmp_path):
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    (recipe_dir / "demo.json").write_text(
        """
        {
          "id": "demo",
          "steps": [
            {"id": "first", "capability": "cap.fail", "continue_on_error": true, "args": {}},
            {"id": "second", "capability": "cap.echo", "args": {}}
          ]
        }
        """,
        encoding="utf-8",
    )
    calls = []

    def fake_run_capability(capability_id, args=None, context=None):
        calls.append(capability_id)
        if capability_id == "cap.fail":
            return {"status": "error"}
        return {"status": "completed"}

    result = recipes.run_recipe("demo", {}, root=str(recipe_dir), executor=fake_run_capability)

    assert result["status"] == "completed"
    assert calls == ["cap.fail", "cap.echo"]


def test_load_recipe_rejects_duplicate_step_ids(tmp_path):
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    (recipe_dir / "demo.json").write_text(
        """
        {
          "id": "demo",
          "steps": [
            {"id": "first", "capability": "cap.echo", "args": {}},
            {"id": "first", "capability": "cap.echo", "args": {}}
          ]
        }
        """,
        encoding="utf-8",
    )

    try:
        recipes.load_recipe("demo", root=str(recipe_dir))
    except ValueError as e:
        assert "duplicate step id: first" in str(e)
    else:
        raise AssertionError("Expected duplicate step error")


def test_template_missing_value_raises(tmp_path):
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    (recipe_dir / "demo.json").write_text(
        """
        {
          "id": "demo",
          "steps": [
            {"id": "first", "capability": "cap.echo", "args": {"value": "{{inputs.topic}}"}}
          ]
        }
        """,
        encoding="utf-8",
    )

    try:
        recipes.run_recipe("demo", {}, root=str(recipe_dir), executor=lambda *args, **kwargs: {})
    except ValueError as e:
        assert "Recipe template value not found: inputs.topic" in str(e)
    else:
        raise AssertionError("Expected missing template value error")
