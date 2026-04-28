import os
import sys
import requests
import json
import logging
from typing import Optional

# Injetar a raiz do projeto no path para encontrar o config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MAX_TOKENS, GEMINI_TEMPERATURE

logger = logging.getLogger(__name__)

def generate_script_from_topic(topic: str, style_prompt: str = "", duration_target: str = "medium") -> Optional[str]:
    """
    v3.0: Gerador de roteiros profissionais em EN-US.
    duration_target: "short" (~60s), "medium" (~3min), "long" (~7min)
    """
    api_key = GEMINI_API_KEY
    if not api_key or "sua_chave" in api_key:
        logger.error("❌ Gemini API Key missing.")
        return None

    duration_map = {
        "short":  ("60 a 90 segundos", "1 a 2 parágrafos densos"),
        "medium": ("3 a 4 minutos",     "4 a 6 parágrafos, cada um com argumento próprio"),
        "long":   ("6 a 8 minutos",     "8 a 10 parágrafos, estrutura de mini-documentário"),
    }
    target_dur, target_struct = duration_map.get(duration_target, duration_map["medium"])

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    
    prompt = f"""
<role>
Você é o roteirista-chefe de um canal faceless de alto CPM no YouTube gringo.
Referências de qualidade: Kurzgesagt, Veritasium, Johnny Harris, Nas Daily.
</role>

<brand_identity>
{style_prompt if style_prompt else "Premium educational content, calm but engaging tone, neutral American English."}
</brand_identity>

<task>
Escreva um roteiro completo para narração TTS sobre: "{topic}"
Duração alvo: {target_dur}
Estrutura: {target_struct}
</task>

<mandatory_structure>
1. HOOK (first 3s): Shocking fact or absurd number. No channel intro.
2. SETUP (~20%): Minimum context to understand the argument.
3. CONFLICT (~50%): The core. Evidence, contrasts, and turns. Micro-tension at end of each paragraph.
4. RESOLUTION (~20%): Unexpected insight or answer.
5. FINAL CTA (~10%): One sentence to make viewer share/comment. Don't mention 'like' or 'subscribe'.
</mandatory_structure>

<rules>
- Language: ENGLISH (American English, neutral).
- Return ONLY spoken text, zero rubrics, zero section titles.
- Paragraphs: 3-5 sentences. Empty line between paragraphs.
- FORBIDDEN: "In this video", "Today we're going to", "Don't forget to subscribe".
- Tone: Authoritative but conversational. Telling an important secret.
</rules>
"""
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        logger.info(f"🧠 Generating {duration_target} script for: {topic}...")
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return text.replace("*", "").strip()
        else:
            logger.error(f"❌ Gemini Error: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--style", default="")
    parser.add_argument("--duration", default="medium")
    args = parser.parse_args()
    
    script = generate_script_from_topic(args.topic, args.style, args.duration)
    if script: print(script)
    else: sys.exit(1)
