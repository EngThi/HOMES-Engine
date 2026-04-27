"""
core/modules/finance_tracker.py — Rastreador financeiro pessoal

Funcionalidades:
  - Registra gasto/receita via linha de comando ou Hub
  - Calcula progresso em direção à meta mensal ($500-1k)
  - Gera relatório mensal com Gemini (insights + sugestões)
  - Dados em output/finance/YYYY-MM.json (simples, sem banco)

Uso direto:
  python -m core.modules.finance_tracker add income 50 "AdSense"
  python -m core.modules.finance_tracker add expense 15 "API key"
  python -m core.modules.finance_tracker report
Acionado pelo Hub:
  {"command": "run_module", "args": ["finance_tracker", "report"]}
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
HUB_BASE    = os.getenv("HOMES_HUB_URL", "http://localhost:8080")
MONTHLY_GOAL = float(os.getenv("MONTHLY_GOAL_USD", "500"))
FINANCE_DIR  = os.path.join("output", "finance")


def _data_file() -> str:
    month = datetime.now().strftime("%Y-%m")
    os.makedirs(FINANCE_DIR, exist_ok=True)
    return os.path.join(FINANCE_DIR, f"{month}.json")


def _load() -> dict:
    path = _data_file()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"income": [], "expense": [], "month": datetime.now().strftime("%Y-%m")}


def _save(data: dict):
    with open(_data_file(), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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


def add_entry(entry_type: str, amount: float, description: str) -> dict:
    data = _load()
    entry = {
        "amount": amount,
        "description": description,
        "date": datetime.now().isoformat(),
    }
    data[entry_type].append(entry)
    _save(data)
    logger.info(f"[finance] +{entry_type}: ${amount} — {description}")
    return entry


def get_summary() -> dict:
    data   = _load()
    income  = sum(e["amount"] for e in data["income"])
    expense = sum(e["amount"] for e in data["expense"])
    net     = income - expense
    progress = (income / MONTHLY_GOAL * 100) if MONTHLY_GOAL else 0
    return {
        "month":    data["month"],
        "income":   income,
        "expense":  expense,
        "net":      net,
        "goal":     MONTHLY_GOAL,
        "progress": f"{progress:.1f}%",
        "entries":  len(data["income"]) + len(data["expense"]),
    }


@register("finance_tracker")
def run(args: list) -> dict:
    """
    args[0] = subcomando: 'report' | 'summary' | 'add'
    Para 'add': args = ['add', 'income'|'expense', amount, description]
    """
    subcmd = args[0] if args else "summary"

    if subcmd == "add" and len(args) >= 4:
        entry_type  = args[1]  # income | expense
        amount      = float(args[2])
        description = args[3]
        entry = add_entry(entry_type, amount, description)
        result = {"module": "finance_tracker", "action": "add", "entry": entry}

    elif subcmd == "report":
        summary = get_summary()
        data    = _load()
        all_entries = [
            f"{e['date'][:10]} +${e['amount']} {e['description']}" for e in data["income"]
        ] + [
            f"{e['date'][:10]} -${e['amount']} {e['description']}" for e in data["expense"]
        ]
        entries_str = "\n".join(all_entries[-20:]) or "Nenhuma entrada ainda"

        prompt = f"""
        Analise meu relatório financeiro do mês {summary['month']}.
        Meta mensal: ${summary['goal']}
        Receita total: ${summary['income']:.2f}
        Despesas: ${summary['expense']:.2f}
        Lucro líquido: ${summary['net']:.2f}
        Progresso na meta: {summary['progress']}

        Entradas:
        {entries_str}

        Gere:
        1. Análise objetiva (2-3 linhas)
        2. Principal problema identificado
        3. 3 ações concretas para aumentar receita do canal faceless
        4. Projeção: se mantiver o ritmo, quanto ganha no mês?

        Seja direto, em português.
        """.strip()

        analysis = _gemini(prompt)
        out_dir   = os.path.join("output", "finance")
        os.makedirs(out_dir, exist_ok=True)
        report_path = os.path.join(out_dir, f"report_{summary['month']}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Relatório Financeiro — {summary['month']}\n\n")
            f.write(f"**Meta:** ${summary['goal']} | **Progresso:** {summary['progress']}\n")
            f.write(f"**Receita:** ${summary['income']:.2f} | **Despesas:** ${summary['expense']:.2f} | **Líquido:** ${summary['net']:.2f}\n\n")
            f.write(f"## Análise Gemini\n\n{analysis}")

        result = {
            "module":      "finance_tracker",
            "action":      "report",
            "summary":     summary,
            "report_file": report_path,
            "analysis":    analysis[:400],
        }

    else:  # summary padrão
        result = {"module": "finance_tracker", "action": "summary", **get_summary()}

    # Notifica Hub
    try:
        requests.post(
            f"{HUB_BASE}/api/sensors",
            json={"module_result": result},
            timeout=3,
        )
    except Exception:
        pass

    return result


if __name__ == "__main__":
    import sys
    out = run(sys.argv[1:] if len(sys.argv) > 1 else ["summary"])
    import json as _json
    print(_json.dumps(out, indent=2, ensure_ascii=False))
