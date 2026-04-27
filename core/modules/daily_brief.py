"""
core/modules/daily_brief.py — Briêfing diário personalizado

Funcionalidades:
  - Gera briêfing do dia com Gemini: prioridades, tech news do nicho, foco
  - Salva em output/briefs/brief_YYYYMMDD.md
  - Ideal para rodar todo dia às 7h via cron/n8n

Uso direto:
  python -m core.modules.daily_brief
Acionado pelo Hub:
  {"command": "run_module", "args": ["daily_brief"]}
"""
import os
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
HUB_BASE = os.getenv("HOMES_HUB_URL", "http://localhost:8080")


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


@register("daily_brief")
def run(args: list) -> dict:
    """
    Gera briêfing diário com:
      - Foco do dia (baseado no dia da semana)
      - Ideia de vídeo para canal faceless (nicho gringa, CPM alto)
      - 3 tarefas de maior impacto
    """
    today     = datetime.now()
    weekday   = today.strftime("%A")  # Monday, Tuesday...
    date_str  = today.strftime("%Y-%m-%d")
    hour      = today.hour
    period    = "manhã" if hour < 12 else ("tarde" if hour < 18 else "noite")
    context   = " ".join(args) if args else ""

    logger.info(f"[daily_brief] Gerando briêfing para {date_str} ({weekday})")

    prompt = f"""
    Você é o assistente pessoal de um criador de conteúdo tecnólogo brasileiro.
    Perfil: estudante de Eng. de Computação, projeto principal = canal YouTube faceless
    em inglês (nicho: psicologia, finance, tech tips, high CPM), meta $500-1k/mês.

    Hoje é {weekday}, {date_str}, {period}.
    Contexto extra: {context if context else 'nenhum'}

    Gere um briêfing diário em português com:

    ## 🎯 Foco do Dia
    (O que MAIS importa fazer hoje — 1 coisa só)

    ## 🎬 Ideia de Vídeo
    (Título clickbait em inglês + 3 pontos-chave do roteiro + CPM estimado)

    ## ✅ Top 3 Tarefas
    (Em ordem de impacto, com tempo estimado)

    ## ⚡ Lembrete Motivacional
    (1 frase curta e real, sem clichê)

    Seja direto, prático e brutalmente honesto.
    """.strip()

    brief_text = _gemini(prompt)

    # Salva
    out_dir = os.path.join("output", "briefs")
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, f"brief_{date_str}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Daily Brief — {date_str}\n\n")
        f.write(brief_text)

    result = {
        "module": "daily_brief",
        "date": date_str,
        "weekday": weekday,
        "output_file": filepath,
        "preview": brief_text[:400],
    }

    try:
        requests.post(
            f"{HUB_BASE}/api/sensors",
            json={"module_result": result},
            timeout=3,
        )
    except Exception:
        pass

    logger.info(f"[daily_brief] Brief salvo → {filepath}")
    return result


if __name__ == "__main__":
    import sys
    ctx = " ".join(sys.argv[1:])
    out = run([ctx] if ctx else [])
    print(f"✅ Brief gerado: {out['output_file']}")
    print(f"\n{out['preview']}")
