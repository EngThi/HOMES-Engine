import requests
import json
import logging
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MAX_TOKENS, GEMINI_TEMPERATURE

# Configuração de Logs
logger = logging.getLogger(__name__)

def generate_script_from_topic(topic):
    api_key = GEMINI_API_KEY
    if not api_key or "sua_chave" in api_key:
        logger.error("❌ Chave da API Gemini não encontrada ou inválida em config/env")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    
    prompt = f"""
    [ROLE]
    Você é um Roteirista Profissional de Vídeos Curtos (Shorts/Reels) estilo "Absolute Cinema".
    
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
            # Limpeza básica (remover asteriscos ou formatação markdown se houver)
            clean_text = generated_text.replace("*", "").strip()
            return clean_text
        else:
            logger.error(f"❌ Erro na API Gemini: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Falha na conexão: {e}")
        return None
