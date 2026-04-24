import os
import sys
import requests
import json
import logging
from typing import Optional

# Injetar a raiz do projeto no path para encontrar o config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MAX_TOKENS, GEMINI_TEMPERATURE

# Configuração de Logs
logger = logging.getLogger(__name__)

def generate_script_from_topic(topic: str, style_prompt: str = "") -> Optional[str]:
    """
    Gera um roteiro otimizado para vídeos curtos usando a API do Gemini.
    """
    api_key = GEMINI_API_KEY
    if not api_key or "sua_chave" in api_key:
        logger.error("❌ Chave da API Gemini não encontrada ou inválida em config/env")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    
    brand_context = f"\n    [CREATOR STYLE]\n    {style_prompt}\n" if style_prompt else ""

    prompt = f"""
    [ROLE]
    Você é um Roteirista Profissional de Vídeos Curtos (Shorts/Reels) estilo "Absolute Cinema".
    {brand_context}
    [TASK]
    Crie um roteiro EM PORTUGUÊS sobre o tema: "{topic}".
    
    [GUIDELINES]
    1. Gancho (0-3s): Uma frase impactante ou pergunta retórica.
    2. Corpo (3-45s): Desenvolvimento rápido, denso e direto.
    3. CTA (Final): Chamada para ação sutil (ex: "Siga para mais").
    4. Tom: Motivacional, Curioso ou Sombrio (depende do tema).
    5. Formatação: Retorne APENAS o texto falado (narração). Não inclua rubricas como [Cena], [Música], etc. O texto deve ser pronto para TTS.
    
    [OUTPUT EXAMPLE]
    Você sabia que 90% das pessoas desistem antes da hora? O fracasso não é o fim, é o degrau. Se você parar agora, nunca saberá o quão perto estava. Continue caminhando.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        logger.info(f"🧠 Enviando tema '{topic}' para o Gemini...")
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            data = response.json()
            generated_text = data['candidates'][0]['content']['parts'][0]['text']
            clean_text = generated_text.replace("*", "").strip()
            return clean_text
        else:
            logger.error(f"❌ Erro na API Gemini: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Falha na conexão: {e}")
        return None

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Gerador de Roteiro AI")
    parser.add_argument("--topic", type=str, required=True, help="Tema do vídeo")
    parser.add_argument("--style", type=str, default="", help="Estilo do criador")
    
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    
    script = generate_script_from_topic(args.topic, args.style)
    if script:
        # Retorna APENAS o texto para que o redirecionamento > funcione perfeitamente
        print(script)
    else:
        sys.exit(1)
