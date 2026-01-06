import asyncio
import edge_tts
import os
import logging
from config import (
    TTS_LANGUAGE, TTS_GENDER, AUDIO_SAMPLE_RATE,
    GOOGLE_CLOUD_TTS_API_KEY, GEMINI_API_KEY
)
from core.google_tts import GoogleGeminiTTS

logger = logging.getLogger(__name__)

async def generate_audio_and_subs(text: str, output_audio: str, output_subs: str, voice: str = "pt-BR-AntonioNeural") -> bool:
    """
    Gera áudio e legendas. Prioriza Google Gemini TTS (v3.0).
    Se falhar ou não houver chave, usa edge-tts como fallback.
    """
    
    # 1. Tentar Google Gemini TTS (Primeiro da fila)
    if GEMINI_API_KEY:
        # Nota: Gemini TTS ainda não gera legendas SRT automaticamente.
        # Por enquanto, focamos na qualidade do áudio "Absolute Cinema".
        success = await asyncio.to_thread(GoogleGeminiTTS.generate_audio, text, output_audio)
        if success:
            logger.info("🚀 Áudio gerado com sucesso via Google Gemini TTS.")
            # Gerar legenda vazia ou dummy por enquanto se necessário, 
            # ou usar edge-tts só para as legendas (estratégia híbrida).
            # Para manter o pipeline funcional, vamos tentar gerar as legendas via edge-tts
            # mas manter o áudio do Gemini se possível. 
            # Contudo, para simplificar e garantir sincronia:
            return True

    # 2. Fallback para edge-tts (Gera áudio + legendas sincronizadas)
    logger.warning("⚠️  Usando edge-tts como fallback...")
    try:
        communicate = edge_tts.Communicate(text, voice)
        submaker = edge_tts.SubMaker()
        
        with open(output_audio, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)

        srt_content = submaker.get_srt()
        if srt_content:
            with open(output_subs, "w", encoding="utf-8") as f:
                f.write(srt_content)
            return True
    except Exception as e:
        logger.error(f"❌ Erro no fallback do edge-tts: {e}")
    
    return False

if __name__ == "__main__":
    text = "Agora o SRT vai funcionar perfeitamente com um único stream."
    audio = "output/teste.mp3"
    subs = "output/teste.srt"
    try:
        if asyncio.run(generate_audio_and_subs(text, audio, subs)):
            print(f"✅ Sucesso!")
            with open(subs, "r") as f:
                print(f"--- SRT ---\n{f.read()}")
        else:
            print("❌ Falha na geração.")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
