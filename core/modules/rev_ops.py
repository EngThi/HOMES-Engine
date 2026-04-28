import json
import os
import logging
from . import register
from google import genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_metrics():
    # Simula dados de um canal em crescimento
    return {
        "videos_generated": 12,
        "monthly_views": 8400,
        "avg_cpm": 5.20,
        "infra_cost": 0.00
    }

@register("rev_ops")
def run(args: list) -> dict:
    load_dotenv()
    data = load_metrics()
    
    revenue = (data["monthly_views"] / 1000) * data["avg_cpm"]
    profit = revenue - data["infra_cost"]
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = f"""
    Canal de Automação Tech. 
    Status: {data['videos_generated']} vídeos, {data['monthly_views']} views, ${revenue:.2f} receita.
    Custo: $0. 
    Dê 1 insight brutal para dobrar a retenção dos vídeos de 5 minutos.
    """
    
    response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
    
    return {
        "module": "rev_ops",
        "metrics": {
            "revenue_usd": round(revenue, 2),
            "profit_usd": round(profit, 2),
            "margin_pct": 100.0
        },
        "ai_strategic_insight": response.text
    }
