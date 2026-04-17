import os, subprocess, sys, time, json
from datetime import datetime
from core.video_maker import generate_video
from core.ai_writer import generate_script_from_topic
from config import validate_config, THEMES, SCRIPTS_DIR, OUTPUT_DIR, GEMINI_API_KEY
from core.error_handler import get_logger, ErrorContext, retry, with_error_context
from core.queue_handler import QueueHandler
from core.branding_loader import BrandingLoader

logger = get_logger(__name__)
CYAN, GREEN, YELLOW, RED, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[0m"

def clear_screen(): os.system('clear')
def print_banner(current_brand="default"):
    clear_screen()
    print(f"{CYAN}🎬 HOMES ENGINE | ABSOLUTE CINEMA v1.8{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")
    print(f"{GREEN}STATUS: ONLINE{RESET} | {YELLOW}BRAND: {current_brand.upper()}{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
    except: return None

def select_brand_menu():
    """Lista as pastas em branding/ e permite escolher uma"""
    brands = [d for d in os.listdir("branding") if os.path.isdir(os.path.join("branding", d))]
    if not brands: return "default"
    
    print(f"\n{CYAN}👤 SELECIONE O PERFIL DE CRIADOR:{RESET}")
    for i, b in enumerate(brands):
        print(f"{YELLOW}[{i+1}]{RESET} {b}")
    
    try:
        choice = int(input(f"\n👉 Escolha (Enter para 1): ") or 1) - 1
        return brands[choice]
    except:
        return "default"

def main_menu(brand="default"):
    print_banner(brand)
    print(f"{YELLOW}[1]{RESET} 🎤 Gravar Roteiro (Voz)")
    print(f"{YELLOW}[2]{RESET} ⌨️  Digitar Roteiro (Texto)")
    print(f"{YELLOW}[3]{RESET} 📋 Colar do Clipboard")
    print(f"{YELLOW}[4]{RESET} 🏃 Renderizar Existente")
    print(f"{YELLOW}[5]{RESET} 🧠 Gerar com IA (Brand Style)")
    print(f"{YELLOW}[6]{RESET} ⚙️  Configurações de Storage")
    print(f"{YELLOW}[7]{RESET} 👤 Trocar Perfil/Brand")
    print(f"{YELLOW}[99]{RESET} 🤖 MODO AUTÔNOMO")
    print(f"{YELLOW}[0]{RESET} ❌ Sair")
    return input(f"\n{CYAN}👉 Opção:{RESET} ")

@retry(max_attempts=3)
def safe_gen_script(topic, style=""): return generate_script_from_topic(topic, style_prompt=style)

def main():
    current_brand = "default"
    storage_pref_file = "config/storage_pref.json"
    
    with ErrorContext("HOMES-Engine"):
        validate_config()
        current_brand = select_brand_menu()
        
        while True:
            choice = main_menu(current_brand)
            if choice == '0': sys.exit()
            if choice == '6': storage_settings_menu(); continue
            if choice == '7': current_brand = select_brand_menu(); continue
            
            # Carrega configs da marca atual
            branding = BrandingLoader(current_brand)
            style_prompt = branding.get_style_prompt()

            script_path = ""
            if choice == '1': 
                content = run_command("termux-speech-to-text")
                if content: 
                    script_path = f"scripts/voice_{int(time.time())}.txt"
                    with open(script_path, "w") as f: f.write(content)
            elif choice == '5':
                topic = input(f"\n{YELLOW}👉 Tema:{RESET} ")
                if topic:
                    print(f"🧠 Aplicando estilo da marca: {current_brand}...")
                    content = safe_gen_script(topic, style_prompt)
                    if content:
                        script_path = f"scripts/ia_{int(time.time())}.txt"
                        with open(script_path, "w") as f: f.write(content)
            elif choice == '4':
                scripts = [f for f in os.listdir("scripts") if f.endswith(".txt")]
                for i, s in enumerate(scripts): print(f"{i+1}. {s}")
                try: script_path = os.path.join("scripts", scripts[int(input("Número: "))-1])
                except: continue

            if script_path:
                print(f"\n{CYAN}🎨 Iniciando Render v1.8 (Marca: {current_brand})...{RESET}")
                generate_video(script_path, brand_name=current_brand)
                input("\n[Enter] para continuar...")

if __name__ == "__main__":
    main()
