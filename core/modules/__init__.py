"""
core/modules/__init__.py — HOMES-Engine Module Registry

Cada módulo é uma função que recebe args: list e retorna um resultado dict.
O Hub pode acionar qualquer módulo via comando remoto: {command: run_module, args: [nome, ...]}
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_REGISTRY = {}


def register(name: str):
    """Decorator para registrar um módulo."""
    def decorator(fn):
        _REGISTRY[name] = fn
        return fn
    return decorator


def run_module(name: str, args: list = None) -> Optional[dict]:
    """Executa um módulo pelo nome. Retorna resultado ou None."""
    if name not in _REGISTRY:
        logger.warning(f"[MODULES] Módulo desconhecido: {name}")
        return None
    try:
        return _REGISTRY[name](args or [])
    except Exception as e:
        logger.error(f"[MODULES] Erro em '{name}': {e}")
        return None


def list_modules() -> list:
    return list(_REGISTRY.keys())


# Auto-importa todos os módulos para registrar
from core.modules import study_planner    # noqa: E402,F401
from core.modules import daily_brief      # noqa: E402,F401
from core.modules import finance_tracker  # noqa: E402,F401
