import os, subprocess, sys, time, json, re
from datetime import datetime
from core.video_maker import generate_video
from core.ai_writer import generate_script_from_topic
from config import validate_config, THEMES, SCRIPTS_DIR, OUTPUT_DIR, GEMINI_API_KEY
from core.error_handler import get_logger, ErrorContext, retry
from core.branding_loader import BrandingLoader

logger = get_logger(__name__)
CYAN, GREEN, YELLOW, RED, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[0m"

def clear_screen(): os.system('clear')
def print_banner(current_brand="default"):
    clear_screen()
    print(f"{CYAN}🎬 HOMES ENGINE | ABSOLUTE CINEMA v2.2 (Shippable){RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")
    print(f"{GREEN}STATUS: ONLINE{RESET} | {YELLOW}BRAND: {current_brand.upper()}{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")

def safe_input(prompt):
    try: return input(prompt).strip()
    except KeyboardInterrupt: print(f"\n\n🛑 {RED}Saindo...{RESET}"); sys.exit()

def select_brand_menu():
    if not os.path.exists("branding"): os.makedirs("branding/default", exist_ok=True)
    brands = [d for d in os.listdir("branding") if os.path.isdir(os.path.join("branding", d))]
    print_banner()
    print(f"\n{CYAN}👤 SELECIONE SEU PERFIL DE CRIADOR:{RESET}")
    for i, b in enumerate(brands): print(f"{YELLOW}[{i+1}]{RESET} {b}")
    c = safe_input(f"\n👉 Escolha (Número): ")
    try: return brands[int(c)-1]
    except: return "default"

def main_menu(brand="default"):
    print_banner(brand)
    print(f"{YELLOW}[1]{RESET} 🎤 Gravar Roteiro (Voz)")
    print(f"{YELLOW}[4]{RESET} 🏃 Renderizar Existente")
    print(f"{YELLOW}[5]{RESET} 🧠 Gerar e Renderizar (Imediato)")
    print(f"{YELLOW}[8]{RESET} 📥 Adicionar à Fila (Queuing)")
    print(f"{YELLOW}[7]{RESET} 👤 Trocar Perfil")
    print(f"{YELLOW}[99]{RESET} 🤖 MODO AUTÔNOMO")
    print(f"{YELLOW}[0]{RESET} ❌ Sair")
    return safe_input(f"\n{CYAN}👉 Opção:{RESET} ")

def main():
    current_brand = "default"
    with ErrorContext("HOMES-Engine"):
        validate_config()
        current_brand = select_brand_menu()
        while True:
            try:
                choice = main_menu(current_brand)
                if choice == '0': break
                if choice == '7': current_brand = select_brand_menu(); continue
                
                script_path = ""
                if choice == '8': # Queuing Mode
                    topic = safe_input("\n👉 Tema do vídeo: ")
                    if topic and topic != '0':
                        print("🧠 Escrevendo roteiro...")
                        content = generate_script_from_topic(topic)
                        if content:
                            filename = f"scripts/{int(time.time())}.pending.txt"
                            with open(filename, "w") as f: f.write(content)
                            print(f"✅ Enfileirado: {filename}")
                            time.sleep(1)

                elif choice == '5': # Immediate
                    topic = safe_input("\n👉 Tema do vídeo: ")
                    if topic:
                        content = generate_script_from_topic(topic)
                        if content:
                            script_path = f"scripts/tmp_{int(time.time())}.txt"
                            with open(script_path, "w") as f: f.write(content)

                elif choice == '4': # Existing
                    scripts = [f for f in os.listdir("scripts") if f.endswith(".txt")]
                    for i, s in enumerate(scripts): print(f"{i+1}. {s}")
                    idx = safe_input("Número: ")
                    try: script_path = os.path.join("scripts", scripts[int(idx)-1])
                    except: continue

                if script_path:
                    print(f"\n{CYAN}🎨 Iniciando v2.2...{RESET}")
                    generate_video(script_path, brand_name=current_brand)
                    safe_input("\n[Enter] para voltar ao menu...")
            
            except Exception as e:
                print(f"\n{RED}❌ Ops! Algo deu errado: {e}{RESET}")
                time.sleep(2)

if __name__ == "__main__":
    main()
