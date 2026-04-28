"""
core/modules/study_planner.py — Módulo de planejamento de estudos

Funcionalidades:
  - Gera plano de estudo semanal com Gemini
  - Salva em output/study/plano_YYYYMMDD.md
  - Reporta para o Hub via POST /api/sensors

Uso direto:
  python -m core.modules.study_planner "Python avancado, NestJS, FFmpeg"
Acionado pelo Hub:
  {"command": "run_module", "args": ["study_planner", "Python, NestJS"]}
"""
import os
import json
import logging
import requests
from datetime import datetime
from . import register

logger = logging.getLogger(__name__)

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/gemini-2.0-flash:generateContent"
)
HUB_BASE   = os.getenv("HOMES_HUB_URL", "http://localhost:8080")


def _gemini(prompt: str) -> str:
    if not GEMINI_KEY:
        return "[GEMINI_API_KEY não configurada]"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(
        f"{GEMINI_URL}?key={GEMINI_KEY}",
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


@register("study_planner")
def run(args: list) -> dict:
    """
    args[0] — string com tópicos de estudo separados por vírgula
    Ex: ["Python avançado, NestJS, Algoritmos"]
    """
    topics = args[0] if args else "Engenharia de Computação, Python, NodeJS"
    today  = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"[study_planner] Gerando plano para: {topics}")

    prompt = f"""
    Você é um mentor de estudos para um estudante de Engenharia de Computação
    que quer trabalhar em big techs (Google, NVIDIA, Microsoft).

    Gere um plano de estudo semanal (7 dias) para os tópicos: {topics}

    Para cada dia inclua:
    - Tópico principal (30-60 min)
    - 1 exercício prático específico
    - 1 recurso gratuito recomendado (link ou nome)

    Formato: Markdown limpo com headers por dia.
    Seja objetivo e prático. Foque em projeção real no mercado.
    """.strip()

    plan_text = _gemini(prompt)

    # Salva arquivo
    out_dir = os.path.join("output", "study")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"plano_{today}.md"
    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Plano de Estudos — {today}\n\n")
        f.write(f"**Tópicos:** {topics}\n\n")
        f.write(plan_text)

    result = {
        "module": "study_planner",
        "date": today,
        "topics": topics,
        "output_file": filepath,
        "preview": plan_text[:300],
    }

    # Notifica Hub
    try:
        requests.post(
            f"{HUB_BASE}/api/sensors",
            json={"module_result": result},
            timeout=3,
        )
    except Exception:
        pass

    logger.info(f"[study_planner] Plano salvo → {filepath}")
    return result


if __name__ == "__main__":
    import sys
    topics = " ".join(sys.argv[1:]) or "Python, NestJS, Algoritmos"
    out = run([topics])
    print(f"✅ Plano gerado: {out['output_file']}")
    print(f"\nPreview:\n{out['preview']}")
