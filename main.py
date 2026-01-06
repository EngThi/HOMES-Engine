import os
import subprocess
import sys
import time
from datetime import datetime
from core.video_maker import generate_video
from core.ai_writer import generate_script_from_topic
from config import (
    validate_config, THEMES, SCRIPTS_DIR, OUTPUT_DIR,
    GEMINI_API_KEY, get_theme, get_output_path
)

# Cores para o Terminal
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def clear_screen():
    os.system('clear')

def print_banner():
    clear_screen()
    print(f"{CYAN}🎬 HOMES ENGINE | ABSOLUTE CINEMA v3.0 PRE-RELEASE{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")
    print(f"{GREEN}STATUS: ONLINE{RESET} | {YELLOW}IA BRAIN: READY{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")

def run_command(command):
    try:
        return subprocess.check_output(command, shell=True).decode('utf-8').strip()
    except subprocess.CalledProcessError:
        return None

def get_voice_input():
    print(f"\n{YELLOW}🎤 Gravando... Fale o seu roteiro agora!{RESET}")
    print(f"{YELLOW}(Aguarde o popup do Google ou fale direto se o microfone ativar){RESET}")
    
    # Tenta capturar o texto via Termux API
    text = run_command("termux-speech-to-text")
    
    if text:
        print(f"\n{GREEN}✅ Capturado:{RESET} {text}")
        return text
    else:
        print(f"\n{RED}❌ Nenhuma voz detectada.{RESET}")
        return None

def save_script(content, topic_slug):
    os.makedirs("scripts", exist_ok=True)
    filename = f"scripts/{topic_slug}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return filename

def main_menu():
    print_banner()
    print(f"{YELLOW}[1]{RESET} 🎤 Gravar Roteiro (Voz)")
    print(f"{YELLOW}[2]{RESET} ⌨️  Digitar Roteiro (Texto)")
    print(f"{YELLOW}[3]{RESET} 📋 Colar do Clipboard")
    print(f"{YELLOW}[4]{RESET} 🏃 Renderizar Arquivo Existente")
    print(f"{YELLOW}[5]{RESET} 🧠 Gerar Roteiro (IA Gemini)")
    print(f"{YELLOW}[0]{RESET} ❌ Sair")
    
    choice = input(f"\n{CYAN}👉 Opção:{RESET} ")
    return choice

def main():
    # Validar config no início
    if not validate_config():
        input("Pressione Enter para continuar mesmo assim...")

    while True:
        choice = main_menu()
        
        script_content = ""
        script_path = ""
        
        if choice == '0':
            print("Saindo...")
            sys.exit()

        elif choice == '1':
            # Modo Voz
            print(f"\n{CYAN}💡 Dica: Fale o roteiro COMPLETO, como se estivesse narrando.{RESET}")
            script_content = get_voice_input()
            if not script_content:
                input("Pressione Enter para tentar novamente...")
                continue

        elif choice == '2':
            # Modo Texto
            print(f"\n{CYAN}📝 Digite seu roteiro (Pressione Enter 2x para finalizar):{RESET}")
            lines = []
            while True:
                line = input()
                if line:
                    lines.append(line)
                else:
                    break
            script_content = "\n".join(lines)

        elif choice == '3':
            # Modo Clipboard
            script_content = run_command("termux-clipboard-get")
            print(f"\n{GREEN}📋 Conteúdo do Clipboard:{RESET}\n{script_content}")

        elif choice == '4':
            # Modo Arquivo Existente
            # Listar scripts
            scripts = [f for f in os.listdir("scripts") if f.endswith(".txt")]
            if not scripts:
                print(f"{RED}Nenhum script encontrado em /scripts.{RESET}")
                input("Enter...")
                continue
                
            print(f"\n{CYAN}📂 Scripts Disponíveis:{RESET}")
            for i, s in enumerate(scripts):
                print(f"{YELLOW}[{i+1}]{RESET} {s}")
            
            try:
                sel = int(input(f"\n{CYAN}👉 Escolha o número:{RESET} ")) - 1
                script_path = os.path.join("scripts", scripts[sel])
            except:
                print("Opção inválida.")
                continue

        elif choice == '5':
            # Modo IA Gemini
            print(f"\n{CYAN}🧠 Digite o TEMA do vídeo (ex: 'Estoicismo', 'Dicas de Python'):{RESET}")
            topic = input(f"{YELLOW}👉 Tema:{RESET} ")
            
            if topic:
                print(f"\n{YELLOW}⏳ Consultando o Cérebro Digital...{RESET}")
                script_content = generate_script_from_topic(topic)
                
                if script_content:
                    print(f"\n{GREEN}📜 Roteiro Gerado:{RESET}\n{'-'*20}\n{script_content}\n{'-'*20}")
                    confirm = input("\nUsar este roteiro? (s/n): ").lower()
                    if confirm != 's':
                        script_content = "" # Descarta

        # Processamento Pós-Input (Para opções 1, 2, 3, 5)
        if choice in ['1', '2', '3', '5'] and script_content:
            # Gerar nome do arquivo baseado no início do texto
            slug = script_content[:20].strip().replace(" ", "_").lower()
            slug = "".join(c for c in slug if c.isalnum() or c == "_")
            if not slug: slug = "sem_titulo"
            
            timestamp = datetime.now().strftime("%H%M%S")
            full_slug = f"ia_{slug}_{timestamp}" if choice == '5' else f"voice_{slug}_{timestamp}"
            
            script_path = save_script(script_content, full_slug)
            print(f"\n{GREEN}💾 Script salvo em: {script_path}{RESET}")

        # Fase de Renderização
        if script_path:
            print(f"\n{CYAN}🎨 Escolha o Tema:{RESET}")
            print("1. Yellow Punch (Padrão)")
            print("2. Cyan Future")
            print("3. Minimal Box")
            
            theme_map = {"1": "yellow_punch", "2": "cyan_future", "3": "minimal_box"}
            theme_choice = input(f"{CYAN}👉 Opção (Enter=1):{RESET} ")
            selected_theme = theme_map.get(theme_choice, "yellow_punch")
            
            print(f"\n{YELLOW}🚀 Iniciando Motor de Renderização...{RESET}")
            try:
                generate_video(script_path, selected_theme)
                print(f"\n{GREEN}✅ Processo Concluído! Verifique a pasta Downloads.{RESET}")
            except Exception as e:
                print(f"{RED}❌ Erro na renderização: {e}{RESET}")
            
            input("\n[Enter] para voltar ao menu...")

if __name__ == "__main__":
    main()