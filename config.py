"""
Centralized Configuration for HOMES-Engine
Gerencia todas as variáveis de configuração do projeto.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

def load_from_secrets(key_name: str) -> str:
    """Fallback para ler do arquivo .secrets se não estiver no ambiente."""
    try:
        secrets_path = Path(__file__).parent / ".secrets"
        if secrets_path.exists():
            with open(secrets_path, "r") as f:
                for line in f:
                    if line.startswith(f"{key_name}="):
                        return line.strip().split("=")[1]
    except Exception:
        pass
    return ""

# ===== PATHS =====
PROJECT_ROOT = Path(__file__).parent.absolute()
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Criar diretórios se não existirem
for dir_path in [SCRIPTS_DIR, OUTPUT_DIR, ASSETS_DIR]:
    dir_path.mkdir(exist_ok=True)

# ===== API KEYS =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or load_from_secrets("GEMINI_API_KEY")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY") or load_from_secrets("POLLINATIONS_API_KEY")
GOOGLE_CLOUD_TTS_API_KEY = os.getenv("GOOGLE_CLOUD_TTS_API_KEY") or load_from_secrets("GOOGLE_CLOUD_TTS_API_KEY")

# ===== TERMUX API =====
USE_TERMUX_API = os.getenv("USE_TERMUX_API", "true").lower() == "true"
USE_VOICE_INPUT = os.getenv("USE_VOICE_INPUT", "false").lower() == "true"

# ===== VIDEO THEMES =====
THEMES = {
    "yellow_punch": {
        "name": "Yellow Punch",
        "bg_color": (255, 193, 7),      # Amarelo brilhante
        "text_color": (33, 33, 33),     # Cinza escuro
        "accent_color": (244, 67, 54),  # Vermelho
        "font_size": 80,
        "style": "bold"
    },
    "cyan_future": {
        "name": "Cyan Future",
        "bg_color": (0, 188, 212),      # Cyan
        "text_color": (255, 255, 255),  # Branco
        "accent_color": (156, 39, 176), # Roxo
        "font_size": 75,
        "style": "modern"
    },
    "minimal_box": {
        "name": "Minimal Box",
        "bg_color": (240, 240, 240),    # Cinza claro
        "text_color": (33, 33, 33),     # Preto
        "accent_color": (0, 150, 136),  # Teal
        "font_size": 70,
        "style": "minimalist"
    }
}

# ===== VIDEO SETTINGS =====
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_DURATION_SECONDS = 60
VIDEO_CODEC = "libx264"

# ===== AUDIO SETTINGS =====
AUDIO_SAMPLE_RATE = 44100
AUDIO_MONO = True
TTS_LANGUAGE = "pt-BR"
TTS_GENDER = "NEUTRAL"
TTS_ENGINE = "gemini" # Opções: "edge" (com legendas perfeitas), "gemini" (voz superior, legendas estimadas)

# ===== AI SETTINGS =====
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_MAX_TOKENS = 2048
GEMINI_TEMPERATURE = 0.7

# ===== VALIDATION =====
def validate_config():
    """
    Valida se todas as configurações essenciais estão presentes.
    """
    errors = []
    
    if not GEMINI_API_KEY:
        errors.append("⚠️  GEMINI_API_KEY não configurada. Modo IA desabilitado.")
    
    if not SCRIPTS_DIR.exists():
        errors.append(f"❌ Diretório {SCRIPTS_DIR} não pode ser criado.")
    
    if errors:
        print("\n⚠️  AVISOS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"  {error}")
        print()
    
    return len(errors) == 0

# ===== HELPERS =====
def get_theme(theme_name: str) -> dict:
    """
    Retorna configurações do tema selecionado.
    """
    return THEMES.get(theme_name, THEMES["yellow_punch"])

def get_output_path(filename: str) -> Path:
    """
    Retorna caminho completo do arquivo de saída.
    """
    return OUTPUT_DIR / filename

# Validar ao importar
if __name__ == "__main__":
    validate_config()
    print("\n✅ Configuração validada!")
    print(f"   Project Root: {PROJECT_ROOT}")
    print(f"   Scripts Dir:  {SCRIPTS_DIR}")
    print(f"   Output Dir:   {OUTPUT_DIR}")
    print(f"   Gemini API:   {'✅ Configurada' if GEMINI_API_KEY else '❌ Não configurada'}")
