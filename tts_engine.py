import asyncio
import edge_tts
import os

async def generate_audio(text, output_file, voice="pt-BR-AntonioNeural"):
    """
    Gera um arquivo de áudio a partir do texto usando Microsoft Edge TTS.
    Vozes sugeridas:
    - pt-BR-AntonioNeural (Masculina, séria)
    - pt-BR-FranciscaNeural (Feminina, suave)
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if __name__ == "__main__":
    # Teste rápido se rodado diretamente
    text = "Este é um teste de áudio do sistema Homes Engine Absolute Cinema."
    output = "output/test_audio.mp3"
    try:
        asyncio.run(generate_audio(text, output))
        print(f"✅ Áudio gerado com sucesso: {output}")
    except Exception as e:
        print(f"❌ Erro ao gerar áudio: {e}")