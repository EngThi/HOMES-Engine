import os, subprocess, sys, time, json, re, argparse
from datetime import datetime
from core.video_maker import generate_video
from core.ai_writer import generate_script_from_topic
from config import validate_config, THEMES, SCRIPTS_DIR, OUTPUT_DIR, GEMINI_API_KEY
from core.error_handler import get_logger, ErrorContext, retry
from core.branding_loader import BrandingLoader

logger = get_logger(__name__)
CYAN, GREEN, YELLOW, RED, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[0m"

def clear_screen(): os.system('clear')
def print_banner(current_brand="demo"):
    clear_screen()
    print(f"{CYAN}🎬 HOMES ENGINE | ABSOLUTE CINEMA v3.0{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")
    print(f"{GREEN}STATUS: ONLINE{RESET} | {YELLOW}BRAND: {current_brand.upper()}{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")

def safe_input(prompt):
    try: return input(prompt).strip()
    except KeyboardInterrupt: print(f"\n\n🛑 {RED}Saindo...{RESET}"); sys.exit()

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except Exception: return None

def select_brand_menu():
    if not os.path.exists("branding"): os.makedirs("branding/demo", exist_ok=True)
    brands = [d for d in os.listdir("branding") if os.path.isdir(os.path.join("branding", d))]
    print_banner()
    print(f"\n{CYAN}👤 SELECIONE SEU PERFIL DE CRIADOR:{RESET}")
    for i, b in enumerate(brands): print(f"{YELLOW}[{i+1}]{RESET} {b}")
    c = safe_input(f"\n👉 Escolha (Número): ")
    try: return brands[int(c)-1]
    except: return "demo"

def main_menu(brand="demo"):
    print_banner(brand)
    print(f"{YELLOW}[1]{RESET} 🎤 Gravar Roteiro (Voz)")
    print(f"{YELLOW}[4]{RESET} 🏃 Renderizar Existente")
    print(f"{YELLOW}[5]{RESET} 🧠 Gerar com IA (Brand Style)")
    print(f"{YELLOW}[8]{RESET} 📥 Adicionar à Fila (Queuing)")
    print(f"{YELLOW}[7]{RESET} 👤 Trocar Perfil")
    print(f"{YELLOW}[99]{RESET} 🤖 MODO AUTÔNOMO")
    print(f"{YELLOW}[0]{RESET} ❌ Sair")
    return safe_input(f"\n{CYAN}👉 Opção:{RESET} ")

def main():
    current_brand = "demo"
    with ErrorContext("HOMES-Engine"):
        validate_config()
        current_brand = select_brand_menu()
        while True:
            choice = main_menu(current_brand)
            if choice == '0': break
            if choice == '7': current_brand = select_brand_menu(); continue
            
            script_path = ""
            if choice == '5':
                topic = safe_input("\n👉 Video topic (English): ")
                dur = safe_input("Duration? [1=Short ~60s / 2=Medium ~3min / 3=Long ~7min]: ")
                dur_map = {"1": "short", "2": "medium", "3": "long"}
                duration_target = dur_map.get(dur, "medium")
                
                if topic:
                    branding = BrandingLoader(current_brand)
                    print(f"🧠 Generating {duration_target} script...")
                    content = generate_script_from_topic(topic, branding.get_style_prompt(), duration_target)
                    if content:
                        script_path = f"scripts/ia_{int(time.time())}.txt"
                        with open(script_path, "w") as f: f.write(content)

            elif choice == '4':
                scripts = [f for f in os.listdir("scripts") if f.endswith(".txt")]
                for i, s in enumerate(scripts): print(f"{i+1}. {s}")
                idx = safe_input("Número: ")
                try: script_path = os.path.join("scripts", scripts[int(idx)-1])
                except: continue

            if script_path:
                print(f"\n{CYAN}🎨 Iniciando Render v3.0...{RESET}")
                generate_video(script_path, brand_name=current_brand)
                safe_input("\n[Enter] para continuar...")

if __name__ == "__main__":
    from core.queue_daemon import queue_daemon
    parser = argparse.ArgumentParser(description="HOMES Engine CLI")
    parser.add_argument("--daemon", action="store_true", help="Inicia em modo daemon de fila")
    parser.add_argument("--brand", default="demo", help="Marca para usar no modo daemon")
    parser.add_argument("--check", action="store_true", help="Verifica o status do sistema")
    
    args = parser.parse_args()
    if args.check:
        print(f"{GREEN}HOMES Engine v3.0 OK{RESET}")
        sys.exit(0)
    if args.daemon: queue_daemon()
    else: main()
