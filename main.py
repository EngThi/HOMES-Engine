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
    print(f"{CYAN}🎬 HOMES ENGINE | ABSOLUTE CINEMA v2.5{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")
    print(f"{GREEN}STATUS: ONLINE{RESET} | {YELLOW}BRAND: {current_brand.upper()}{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")

def select_brand_menu():
    brands = [d for d in os.listdir("branding") if os.path.isdir(os.path.join("branding", d))]
    if not brands: return "default"
    print(f"\n{CYAN}👤 SELECIONE O PERFIL DE CRIADOR:{RESET}")
    for i, b in enumerate(brands): print(f"{YELLOW}[{i+1}]{RESET} {b}")
    try:
        choice = int(input(f"\n👉 Escolha (Enter para 1): ") or 1) - 1
        return brands[choice]
    except: return "default"

def main_menu(brand="default"):
    print_banner(brand)
    print(f"{YELLOW}[1]{RESET} 🎤 Gravar Roteiro (Voz)")
    print(f"{YELLOW}[4]{RESET} 🏃 Renderizar Existente")
    print(f"{YELLOW}[5]{RESET} 🧠 Gerar e Renderizar (Imediato)")
    print(f"{YELLOW}[8]{RESET} 📥 Adicionar à Fila (Queuing)")
    print(f"{YELLOW}[6]{RESET} ⚙️  Configurações de Storage")
    print(f"{YELLOW}[7]{RESET} 👤 Trocar Perfil/Brand")
    print(f"{YELLOW}[99]{RESET} 🤖 MODO AUTÔNOMO (Processar Fila)")
    print(f"{YELLOW}[0]{RESET} ❌ Sair")
    return input(f"\n{CYAN}👉 Opção:{RESET} ")

def autonomous_loop(brand="default"):
    """Loop de processamento automático de arquivos .pending.txt"""
    while True:
        try:
            pending = [f for f in os.listdir("scripts") if f.endswith(".pending.txt")]
            if pending:
                for script_name in pending:
                    path = os.path.join("scripts", script_name)
                    print(f"\n🚀 {CYAN}Processando:{RESET} {script_name}")
                    generate_video(path, brand_name=brand)
                    os.rename(path, path.replace(".pending.txt", ".done.txt"))
                    print(f"✅ {GREEN}Concluído!{RESET}")
                    time.sleep(2)
            else:
                print_banner(brand)
                print(f"\n{YELLOW}📭 Fila vazia. Aguardando novos arquivos...{RESET}")
                time.sleep(10)
        except KeyboardInterrupt: break

def slugify(text):
    return re.sub(r'[\W_]+', '_', text).lower()[:20]

def queuing_mode(brand="default"):
    """Modo para adicionar roteiros à fila rapidamente"""
    branding = BrandingLoader(brand)
    style = branding.get_style_prompt()
    
    while True:
        print_banner(brand)
        print(f"\n{CYAN}📥 MODO QUEUING (Adicionar à Fila){RESET}")
        topic = input(f"\n👉 Digite o TEMA (ou '0' para voltar): ")
        if topic == '0': break
        
        print(f"🧠 Gerando roteiro profissional para: {topic}...")
        content = generate_script_from_topic(topic, style)
        if content:
            filename = f"scripts/{slugify(topic)}.pending.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"\n{GREEN}✅ Adicionado à fila: {filename}{RESET}")
            time.sleep(1.5)

def main():
    current_brand = "default"
    with ErrorContext("HOMES-Engine"):
        validate_config()
        current_brand = select_brand_menu()
        while True:
            choice = main_menu(current_brand)
            if choice == '0': sys.exit()
            if choice == '6': storage_settings_menu(); continue
            if choice == '7': current_brand = select_brand_menu(); continue
            if choice == '99': autonomous_loop(current_brand); continue
            if choice == '8': queuing_mode(current_brand); continue
            
            script_path = ""
            if choice == '5':
                topic = input(f"\n{YELLOW}👉 Tema:{RESET} ")
                if topic:
                    branding = BrandingLoader(current_brand)
                    content = generate_script_from_topic(topic, branding.get_style_prompt())
                    if content:
                        script_path = f"scripts/ia_{int(time.time())}.txt"
                        with open(script_path, "w") as f: f.write(content)
            elif choice == '4':
                scripts = [f for f in os.listdir("scripts") if f.endswith((".txt", ".done.txt"))]
                for i, s in enumerate(scripts): print(f"{i+1}. {s}")
                try: script_path = os.path.join("scripts", scripts[int(input("Número: "))-1])
                except: continue

            if script_path:
                generate_video(script_path, brand_name=current_brand)
                input("\n[Enter] para continuar...")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HOMES Engine CLI")
    parser.add_argument("--daemon", action="store_true", help="Inicia em modo daemon de fila")
    parser.add_argument("--brand", default="default", help="Marca para usar no modo daemon")
    
    args = parser.parse_args()
    
    if args.daemon:
        from scripts.queue_daemon import run_daemon
        run_daemon(args.brand)
    else:
        main()
