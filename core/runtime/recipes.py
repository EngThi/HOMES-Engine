from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .capabilities import CapabilityContext
from .events import record_event


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
    return recipe


def run_recipe(
    recipe_id: str,
    inputs: Dict[str, Any] | None = None,
    context: CapabilityContext | None = None,
    root: str = "recipes",
    executor: Any = None,
) -> Dict[str, Any]:
    recipe = load_recipe(recipe_id, root=root)
    inputs = inputs or {}
    context = context or CapabilityContext()
    outputs: Dict[str, Any] = {}
    steps_result = []

    record_event(context, "recipe.started", {"id": recipe_id, "inputs": inputs})
    for index, step in enumerate(recipe.get("steps", []), start=1):
        step_id = step.get("id") or f"step_{index}"
        capability_id = step.get("capability")
        if not capability_id:
            raise ValueError(f"Recipe step {step_id} is missing capability")

        args = _resolve_templates(step.get("args", {}), inputs, outputs)
        record_event(context, "recipe.step.started", {"recipe": recipe_id, "step": step_id, "capability": capability_id})
        if executor is None:
            from .default_capabilities import run_capability

            executor = run_capability
        output = executor(capability_id, args=args, context=context)
        outputs[step_id] = output
        steps_result.append(
            {
                "id": step_id,
                "capability": capability_id,
                "status": output.get("status", "completed") if isinstance(output, dict) else "completed",
                "output": output,
            }
        )
        record_event(context, "recipe.step.completed", {"recipe": recipe_id, "step": step_id, "status": steps_result[-1]["status"]})

    result = {"status": "completed", "id": recipe_id, "steps": steps_result}
    record_event(context, "recipe.completed", {"id": recipe_id, "steps": len(steps_result)})
    return result


def _resolve_templates(value: Any, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_templates(item, inputs, outputs) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_templates(item, inputs, outputs) for item in value]
    if isinstance(value, str):
        return _resolve_string(value, inputs, outputs)
    return value


def _resolve_string(value: str, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
    resolved = value
    for key, item in inputs.items():
        resolved = resolved.replace(f"{{{{inputs.{key}}}}}", str(item))
    for step_id, output in outputs.items():
        if isinstance(output, dict):
            for key, item in output.items():
                resolved = resolved.replace(f"{{{{steps.{step_id}.{key}}}}}", str(item))
    return resolved
