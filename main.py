import os, subprocess, sys, time, json
from datetime import datetime
from core.video_maker import generate_video
from core.ai_writer import generate_script_from_topic
from config import validate_config, THEMES, SCRIPTS_DIR, OUTPUT_DIR, GEMINI_API_KEY
from core.error_handler import get_logger, ErrorContext, retry, with_error_context
from core.queue_handler import QueueHandler

logger = get_logger(__name__)
CYAN, GREEN, YELLOW, RED, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[0m"

def clear_screen(): os.system('clear')
def print_banner():
    clear_screen()
    print(f"{CYAN}🎬 HOMES ENGINE | ABSOLUTE CINEMA v1.7{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")
    print(f"{GREEN}STATUS: ONLINE{RESET} | {YELLOW}IA BRAIN: READY{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
    except: return None

def get_voice_input():
    print(f"\n{YELLOW}🎤 Gravando... Fale o seu roteiro agora!{RESET}")
    text = run_command("termux-speech-to-text")
    if text: print(f"\n{GREEN}✅ Capturado:{RESET} {text}"); return text
    return None

def main_menu():
    print_banner()
    print(f"{YELLOW}[1]{RESET} 🎤 Gravar Roteiro (Voz)")
    print(f"{YELLOW}[2]{RESET} ⌨️  Digitar Roteiro (Texto)")
    print(f"{YELLOW}[3]{RESET} 📋 Colar do Clipboard")
    print(f"{YELLOW}[4]{RESET} 🏃 Renderizar Arquivo Existente")
    print(f"{YELLOW}[5]{RESET} 🧠 Gerar Roteiro (IA Gemini)")
    print(f"{YELLOW}[6]{RESET} ⚙️  Configurações de Armazenamento")
    print(f"{YELLOW}[99]{RESET} 🤖 MODO AUTÔNOMO (Fila/Poller)")
    print(f"{YELLOW}[0]{RESET} ❌ Sair")
    return input(f"\n{CYAN}👉 Opção:{RESET} ")

def storage_settings_menu():
    config_file = "config/storage_pref.json"
    os.makedirs("config", exist_ok=True)
    pref = {"mode": "default", "path": "/sdcard/Download/"}
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            try: pref = json.load(f)
            except: pass
    while True:
        clear_screen()
        print(f"{CYAN}⚙️ CONFIGURAÇÕES DE ARMAZENAMENTO (Android Style){RESET}")
        print(f"Modo: {pref['mode'].upper()} | Pasta: {pref['path']}")
        print("-" * 30)
        print(f"{YELLOW}[1]{RESET} Padrão (Downloads)")
        print(f"{YELLOW}[2]{RESET} Sempre Perguntar (Manual)")
        print(f"{YELLOW}[3]{RESET} Pasta Customizada")
        print(f"{YELLOW}[0]{RESET} Voltar")
        c = input(f"\n👉 Opção: ")
        if c == '0': break
        if c == '1': pref = {"mode": "default", "path": "/sdcard/Download/"}
        if c == '2': pref["mode"] = "ask"
        if c == '3':
            p = input("\nCaminho (ex: /sdcard/Videos/): ")
            if p: pref = {"mode": "default", "path": p}
        with open(config_file, "w") as f: json.dump(pref, f)
        print(f"✅ Salvo!"); time.sleep(1)

@retry(max_attempts=3)
def safe_gen_script(topic): return generate_script_from_topic(topic)

def main():
    storage_pref_file = "config/storage_pref.json"
    with ErrorContext("HOMES-Engine"):
        queue = QueueHandler(n8n_webhook_url=os.getenv("N8N_WEBHOOK_URL"))
        validate_config()
        while True:
            choice = main_menu()
            if choice == '0': sys.exit()
            if choice == '6': storage_settings_menu(); continue
            
            script_path = ""
            if choice == '1': 
                content = get_voice_input()
                if content: 
                    script_path = f"scripts/voice_{int(time.time())}.txt"
                    with open(script_path, "w") as f: f.write(content)
            elif choice == '5':
                topic = input(f"\n{YELLOW}👉 Tema:{RESET} ")
                if topic:
                    content = safe_gen_script(topic)
                    if content:
                        script_path = f"scripts/ia_{int(time.time())}.txt"
                        with open(script_path, "w") as f: f.write(content)
            elif choice == '4':
                scripts = [f for f in os.listdir("scripts") if f.endswith(".txt")]
                for i, s in enumerate(scripts): print(f"{i+1}. {s}")
                try: script_path = os.path.join("scripts", scripts[int(input("Número: "))-1])
                except: continue

            if script_path:
                pref = {"mode": "default", "path": "/sdcard/Download/"}
                if os.path.exists(storage_pref_file):
                    with open(storage_pref_file, "r") as f: pref = json.load(f)
                
                target = pref["path"]
                if pref["mode"] == "ask":
                    print(f"\n{YELLOW}📂 Onde salvar o vídeo?{RESET}")
                    ans = input(f"Caminho (Enter para {target}): ")
                    if ans: target = ans
                
                print(f"\n{CYAN}🎨 Iniciando Render v1.7...{RESET}")
                generate_video(script_path)
                # O video_maker já salva em Downloads por padrão na v1.7
                # No futuro podemos passar o 'target' para o generate_video
                input("\n[Enter] para continuar...")

if __name__ == "__main__":
    main()
