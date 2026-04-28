import os
import time
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from . import register

load_dotenv()
logger = logging.getLogger(__name__)

from core.key_utils import get_gemini_keys

class TrendModel:
    def __init__(self):
        self.keys = get_gemini_keys()
        self.current_idx = 0

    def ask(self, prompt: str):
        for _ in range(len(self.keys)):
            try:
                client = genai.Client(api_key=self.keys[self.current_idx])
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                return response.text
            except Exception as e:
                logger.warning(f"⚠️ TrendModel falhou com Key {self.current_idx}: {e}")
                self.current_idx = (self.current_idx + 1) % len(self.keys)
        return None

@register("trend_intelligence")
def run(args: list) -> dict:
    import json
    with open("profile.json") as f: profile = json.load(f)
    
    logger.info("📡 Scrapeando tendências de tecnologia...")
    feeds = profile.get("preferences", {}).get("rss_feeds", ["https://hnrss.org/frontpage"])
    
    top_news = []
    for url in feeds:
        try:
            resp = requests.get(url, timeout=10)
            root = ET.fromstring(resp.content)
            for item in root.findall('./channel/item')[:3]:
                top_news.append(f"- {item.find('title').text} ({item.find('link').text})")
        except: pass

    news_context = "\n".join(top_news)
    model = TrendModel()
    
    prompt = f"""
    Você é um produtor viral de YouTube. Baseado nestas notícias:
    {news_context}

    Ação: Escolha o tópico com maior potencial de retenção.
    Tarefa: Escreva um script de 1 minuto em inglês (Shorts) focando em curiosidade extrema.
    Formato: Apenas o texto falado, sem rubricas.
    """
    
    script = model.ask(prompt)
    
    if script:
        # Engatilha a fila do Engine
        from config import SCRIPTS_DIR
        file_name = f"auto_trend_{int(time.time())}.txt"
        file_path = os.path.join(SCRIPTS_DIR, file_name)
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(script)
        
        return {"status": "success", "news_scraped": len(top_news), "script_queued": file_path}
    
    return {"status": "error", "message": "Falha ao gerar script"}
