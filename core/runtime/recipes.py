from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .capabilities import CapabilityContext
from .events import record_event


TEMPLATE_PATTERN = re.compile(r"{{\s*([^{}]+)\s*}}")


def list_recipes(root: str = "recipes") -> List[Dict[str, Any]]:
    root_path = Path(root)
    if not root_path.exists():
        return []
    recipes = []
    for path in sorted(root_path.glob("*.json")):
        recipe = load_recipe(path.stem, root=root)
        recipes.append(
            {
                "id": recipe.get("id", path.stem),
                "name": recipe.get("name", path.stem),
                "description": recipe.get("description", ""),
                "required_inputs": recipe.get("required_inputs", []),
                "steps": len(recipe.get("steps", [])),
            }
        )
    return recipes


def load_recipe(recipe_id: str, root: str = "recipes") -> Dict[str, Any]:
    path = Path(root) / f"{recipe_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Recipe not found: {recipe_id}")
    with path.open("r", encoding="utf-8") as f:
        recipe = json.load(f)
    if not isinstance(recipe, dict):
        raise ValueError(f"Recipe must be a JSON object: {recipe_id}")
    recipe.setdefault("id", recipe_id)
    recipe.setdefault("steps", [])
    validate_recipe(recipe)
    return recipe


def validate_recipe(recipe: Dict[str, Any]) -> None:
    if not recipe.get("id"):
        raise ValueError("Recipe id is required")
    required_inputs = recipe.get("required_inputs", [])
    if not isinstance(required_inputs, list):
        raise ValueError(f"Recipe {recipe['id']} required_inputs must be a list")
    defaults = recipe.get("input_defaults", {})
    if defaults and not isinstance(defaults, dict):
        raise ValueError(f"Recipe {recipe['id']} input_defaults must be an object")
    steps = recipe.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError(f"Recipe {recipe['id']} steps must be a list")

    seen = set()
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Recipe {recipe['id']} step {index} must be an object")
        step_id = step.get("id") or f"step_{index}"
        if step_id in seen:
            raise ValueError(f"Recipe {recipe['id']} has duplicate step id: {step_id}")
        seen.add(step_id)
        if not step.get("capability"):
            raise ValueError(f"Recipe step {step_id} is missing capability")
        if "args" in step and not isinstance(step["args"], dict):
            raise ValueError(f"Recipe step {step_id} args must be an object")


def run_recipe(
    recipe_id: str,
    inputs: Dict[str, Any] | None = None,
    context: CapabilityContext | None = None,
    root: str = "recipes",
    executor: Any = None,
) -> Dict[str, Any]:
    recipe = load_recipe(recipe_id, root=root)
    inputs = _merge_inputs(recipe, inputs or {})
    context = context or CapabilityContext()
    outputs: Dict[str, Any] = {}
    steps_result = []
    _require_inputs(recipe, inputs)

    record_event(context, "recipe.started", {"id": recipe_id, "inputs": inputs})
    for index, step in enumerate(recipe.get("steps", []), start=1):
        step_id = step.get("id") or f"step_{index}"
        capability_id = step.get("capability")
        args = _resolve_templates(step.get("args", {}), inputs, outputs)
        record_event(context, "recipe.step.started", {"recipe": recipe_id, "step": step_id, "capability": capability_id})
        if executor is None:
            from .default_capabilities import run_capability

            executor = run_capability
        output = executor(capability_id, args=args, context=context)
        status = output.get("status", "completed") if isinstance(output, dict) else "completed"
        outputs[step_id] = output
        steps_result.append(
            {
                "id": step_id,
                "capability": capability_id,
                "status": status,
                "output": output,
            }
        )
        record_event(context, "recipe.step.completed", {"recipe": recipe_id, "step": step_id, "status": status})
        if status == "error" and not step.get("continue_on_error", False):
            result = {"status": "error", "id": recipe_id, "failed_step": step_id, "steps": steps_result}
            record_event(context, "recipe.failed", {"id": recipe_id, "failed_step": step_id})
            return result

    result = {"status": "completed", "id": recipe_id, "steps": steps_result}
    record_event(context, "recipe.completed", {"id": recipe_id, "steps": len(steps_result)})
    return result


def _merge_inputs(recipe: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(recipe.get("input_defaults") or {})
    merged.update(inputs)
    return merged


def _require_inputs(recipe: Dict[str, Any], inputs: Dict[str, Any]) -> None:
    missing = [key for key in recipe.get("required_inputs", []) if key not in inputs or inputs[key] in ("", None)]
    if missing:
        raise ValueError(f"Recipe {recipe['id']} missing required inputs: {', '.join(missing)}")


def _resolve_templates(value: Any, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_templates(item, inputs, outputs) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_templates(item, inputs, outputs) for item in value]
    if isinstance(value, str):
        return _resolve_string(value, inputs, outputs)
    return value


def _resolve_string(value: str, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        expression = match.group(1).strip()
        if expression.startswith("inputs."):
            key = expression.removeprefix("inputs.")
            return str(_lookup(inputs, key, expression))
        if expression.startswith("steps."):
            parts = expression.split(".", 2)
            if len(parts) != 3:
                raise ValueError(f"Invalid recipe template: {match.group(0)}")
            step_id, key = parts[1], parts[2]
            if step_id not in outputs:
                raise ValueError(f"Recipe template references unavailable step: {step_id}")
            output = outputs[step_id]
            if not isinstance(output, dict):
                raise ValueError(f"Recipe step output is not an object: {step_id}")
            return str(_lookup(output, key, expression))
        raise ValueError(f"Unsupported recipe template: {match.group(0)}")

    return TEMPLATE_PATTERN.sub(replace, value)


def _lookup(source: Dict[str, Any], dotted_key: str, expression: str) -> Any:
    value: Any = source
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Recipe template value not found: {expression}")
        value = value[part]
    return value
