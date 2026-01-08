from core.gemini_tts import GeminiTTS

def test_gemini_voice():
    print("🧪 Iniciando Teste de Voz Gemini...")
    tts = GeminiTTS()
    
    # Teste 1: Voz Simples
    print("1. Gerando áudio simples...")
    tts.generate(
        "Este é um teste oficial do sistema Homes Engine rodando no Termux.", 
        "output/cache/test_gemini_single.wav", 
        voice="Fenrir"
    )
    
    # Teste 2: Multi-Speaker
    print("2. Gerando diálogo...")
    dialogue = """
    User: O sistema está operacional?
    System: Afirmativo. Todos os núcleos online.
    """
    config = {"User": "Puck", "System": "Kore"}
    tts.generate_multi_speaker(
        dialogue, 
        "output/cache/test_gemini_multi.wav", 
        speakers_config=config
    )
    print("✅ Teste concluído! Verifique a pasta output/cache.")

if __name__ == "__main__":
    test_gemini_voice()
