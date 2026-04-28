import os
from dotenv import load_dotenv

load_dotenv()

def get_gemini_keys():
    """Retorna uma lista de todas as chaves Gemini configuradas no .env."""
    keys = []
    # Tenta ler GEMINI_API_KEY, GEMINI_KEY_2, GEMINI_KEY_3, etc.
    main_key = os.getenv("GEMINI_API_KEY")
    if main_key and "sua_chave" not in main_key:
        keys.append(main_key)
        
    for i in range(2, 10):
        key = os.getenv(f"GEMINI_KEY_{i}")
        if key:
            keys.append(key)
            
    # Fallback se nada for encontrado
    if not keys:
        return ["AIZA_DUMMY_KEY_FOR_INITIALIZATION"]
        
    return keys
