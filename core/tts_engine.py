import asyncio
import edge_tts
import os
from config import (
    TTS_LANGUAGE, TTS_GENDER, AUDIO_SAMPLE_RATE,
    GOOGLE_CLOUD_TTS_API_KEY
)

async def generate_audio_and_subs(text: str, output_audio: str, output_subs: str, voice: str = "pt-BR-AntonioNeural") -> bool:
    """
    Gera áudio e SRT em um único stream.
    """
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
