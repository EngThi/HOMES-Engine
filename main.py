import os, subprocess, sys, time, json, argparse
from core.video_maker import generate_video
from core.ai_writer import generate_script_from_topic
from config import validate_config
from core.error_handler import get_logger, ErrorContext
from core.branding_loader import BrandingLoader
from core.videolm_client import (
    _base_url,
    engine_demo_url,
    fetch_engine_health,
    fetch_engine_manifest,
    poll_notebooklm_video,
    resolve_video_url,
    submit_notebooklm_video,
)

logger = get_logger(__name__)
CYAN, GREEN, YELLOW, RED, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[0m"
DEFAULT_DEMO_SCRIPT = "scripts/e2e_engine_test.txt"
NOTEBOOKLM_STYLES = [
    "classic",
    "whiteboard",
    "watercolor",
    "anime",
    "kawaii",
    "retro_print",
    "heritage",
    "paper_craft",
    "custom",
]

def clear_screen(): os.system('clear')
def print_banner(current_brand="demo"):
    clear_screen()
    print(f"{CYAN}🎬 HOMES ENGINE | ABSOLUTE CINEMA v3.0{RESET}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")
    print(f"{GREEN}STATUS: ONLINE{RESET} | {YELLOW}BRAND: {current_brand.upper()}{RESET}")
    print(f"{GREEN}VIDEOLM:{RESET} {_base_url()}")
    print(f"{CYAN}─────────────────────────────────────────────────{RESET}")

def safe_input(prompt):
    try: return input(prompt).strip()
    except EOFError: return ""
    except KeyboardInterrupt: print(f"\n\n🛑 {RED}Saindo...{RESET}"); sys.exit()

def run_command(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except Exception: return None

def available_brands():
    if not os.path.exists("branding"): os.makedirs("branding/demo", exist_ok=True)
    return [d for d in os.listdir("branding") if os.path.isdir(os.path.join("branding", d))]

def select_brand_menu():
    brands = available_brands()
    print_banner()
    print(f"\n{CYAN}👤 SELECIONE SEU PERFIL DE CRIADOR:{RESET}")
    for i, b in enumerate(brands): print(f"{YELLOW}[{i+1}]{RESET} {b}")
    c = safe_input(f"\n👉 Escolha (Número): ")
    try: return brands[int(c)-1]
    except: return "demo"

def main_menu(brand="demo"):
    print_banner(brand)
    print(f"{YELLOW}[1]{RESET} 🌐 Abrir/usar Hosted Demo")
    print(f"{YELLOW}[2]{RESET} ✅ Checar VideoLM Health")
    print(f"{YELLOW}[3]{RESET} 📋 Mostrar Manifest do Engine")
    print(f"{YELLOW}[4]{RESET} 🏃 Renderizar Script Existente")
    print(f"{YELLOW}[5]{RESET} 🧠 Gerar Roteiro com IA e Renderizar")
    print(f"{YELLOW}[6]{RESET} 🎬 Demo CLI rápida")
    print(f"{YELLOW}[7]{RESET} 👤 Trocar Perfil")
    print(f"{YELLOW}[8]{RESET} 📥 Modo Fila Local")
    print(f"{YELLOW}[9]{RESET} 🔌 Modo Hub")
    print(f"{YELLOW}[10]{RESET} 📚 NotebookLM Video")
    print(f"{YELLOW}[0]{RESET} ❌ Sair")
    return safe_input(f"\n{CYAN}👉 Opção:{RESET} ")

def list_scripts():
    if not os.path.isdir("scripts"):
        return []
    return sorted(f for f in os.listdir("scripts") if f.endswith(".txt"))

def choose_existing_script():
    scripts = list_scripts()
    if not scripts:
        print(f"{RED}Nenhum script .txt encontrado em scripts/.{RESET}")
        return ""
    print(f"\n{CYAN}Scripts disponíveis:{RESET}")
    for i, s in enumerate(scripts, start=1):
        print(f"{YELLOW}[{i}]{RESET} {s}")
    idx = safe_input("Número: ")
    try:
        return os.path.join("scripts", scripts[int(idx)-1])
    except Exception:
        print(f"{RED}Opção inválida.{RESET}")
        return ""

def print_health():
    try:
        health = fetch_engine_health()
        print(f"{GREEN}VideoLM OK{RESET}: {health.get('service', 'unknown')}")
        print(f"Base URL: {health.get('baseUrl', _base_url())}")
        print(f"Timestamp: {health.get('timestamp', '-')}")
        return True
    except Exception as e:
        print(f"{RED}VideoLM indisponível:{RESET} {e}")
        return False

def print_manifest_summary():
    try:
        manifest = fetch_engine_manifest()
        public = manifest.get("publicEndpoints", {})
        caps = manifest.get("capabilities", {})
        print(f"{GREEN}{manifest.get('name', 'VideoLM')}{RESET} {manifest.get('version', '')}")
        print(f"Base URL: {manifest.get('baseUrl', _base_url())}")
        print(f"Demo assemble: {public.get('videoDemoAssemble', {}).get('url', '-')}")
        print(f"Status: {public.get('videoStatus', {}).get('urlTemplate', '-')}")
        print(f"Max images: {caps.get('maxImagesPerRender', '-')}")
        print(f"Max upload/file: {caps.get('maxUploadMbPerFile', '-')} MB")
        return True
    except Exception as e:
        print(f"{RED}Falha lendo manifest:{RESET} {e}")
        return False

def render_script(script_path, brand):
    if not script_path:
        return None
    print(f"\n{CYAN}🎨 Iniciando render pelo Engine...{RESET}")
    output = generate_video(script_path, brand_name=brand)
    if output:
        print(f"{GREEN}Render concluído:{RESET} {output}")
    else:
        print(f"{RED}Render falhou. Veja logs acima.{RESET}")
    return output

def generate_ai_script(brand):
    topic = safe_input("\n👉 Video topic (English): ")
    dur = safe_input("Duration? [1=Short ~60s / 2=Medium ~3min / 3=Long ~7min]: ")
    dur_map = {"1": "short", "2": "medium", "3": "long"}
    duration_target = dur_map.get(dur, "medium")
    if not topic:
        return ""
    branding = BrandingLoader(brand)
    print(f"🧠 Generating {duration_target} script...")
    content = generate_script_from_topic(topic, branding.get_style_prompt(), duration_target)
    if not content:
        print(f"{RED}Falha ao gerar roteiro com IA.{RESET}")
        return ""
    script_path = f"scripts/ia_{int(time.time())}.txt"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)
    return script_path

def print_hosted_demo():
    print(f"{GREEN}Hosted demo:{RESET} {engine_demo_url()}")
    print("Use essa página para reviewers: galeria, temas prontos, geração determinística e player final.")

def parse_csv_values(values):
    parsed = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                parsed.append(part)
    return parsed

def validate_notebooklm_style(style, style_prompt=""):
    if style not in NOTEBOOKLM_STYLES:
        raise ValueError(f"Invalid NotebookLM style '{style}'. Use one of: {', '.join(NOTEBOOKLM_STYLES)}")
    if style == "custom" and not style_prompt.strip():
        raise ValueError("stylePrompt is required when style=custom")
    return True

def choose_notebooklm_style():
    print(f"\n{CYAN}NotebookLM styles:{RESET}")
    for i, style in enumerate(NOTEBOOKLM_STYLES, start=1):
        print(f"{YELLOW}[{i}]{RESET} {style}")
    raw = safe_input("Style [paper_craft]: ")
    if not raw:
        return "paper_craft"
    if raw.isdigit():
        try:
            return NOTEBOOKLM_STYLES[int(raw) - 1]
        except Exception:
            return "paper_craft"
    return raw

def submit_notebooklm_from_cli(
    project_id="",
    theme="",
    urls=None,
    style="paper_craft",
    title="",
    asset_paths=None,
    style_prompt="",
    live_research=False,
    notebook_id="",
    profile_id="default",
    interactive=True,
):
    if interactive:
        project_id = project_id or safe_input("Project ID: ")
        title = title or safe_input("Title (optional): ")
        theme = theme or safe_input("Theme: ")
    urls = parse_csv_values(urls)
    if interactive and not urls:
        url = safe_input("Source URL (optional): ")
        urls = [url] if url else []
    asset_paths = parse_csv_values(asset_paths)
    if interactive and not style:
        style = choose_notebooklm_style()
    style = style or "paper_craft"
    if interactive and style == "custom" and not style_prompt:
        style_prompt = safe_input("Custom style prompt: ")
    if interactive and not notebook_id:
        notebook_id = safe_input("Existing notebookId (optional): ")
    if interactive and not profile_id:
        profile_id = safe_input("Profile ID [default]: ") or "default"
    validate_notebooklm_style(style, style_prompt)
    result = submit_notebooklm_video(
        project_id=project_id,
        title=title,
        theme=theme,
        urls=urls,
        asset_paths=asset_paths,
        style=style,
        style_prompt=style_prompt,
        live_research=live_research,
        notebook_id=notebook_id,
        profile_id=profile_id,
    )
    print(json.dumps(result, indent=2))
    return result

def poll_notebooklm_from_cli(project_id):
    result = poll_notebooklm_video(project_id)
    print(json.dumps(result, indent=2))
    video_url = resolve_video_url(result.get("videoUrl") or result.get("videoPath") or "")
    if video_url:
        print(f"{GREEN}Video:{RESET} {video_url}")
    return result

def main():
    current_brand = "demo"
    with ErrorContext("HOMES-Engine"):
        validate_config()
        current_brand = select_brand_menu()
        while True:
            choice = main_menu(current_brand)
            if choice == '0': break
            if choice == '7': current_brand = select_brand_menu(); continue
            if choice == '1':
                print_hosted_demo()
            elif choice == '2':
                print_health()
            elif choice == '3':
                print_manifest_summary()
            elif choice == '4':
                render_script(choose_existing_script(), current_brand)
            elif choice == '5':
                render_script(generate_ai_script(current_brand), current_brand)
            elif choice == '6':
                render_script(DEFAULT_DEMO_SCRIPT, current_brand)
            elif choice == '8':
                from core.queue_daemon import queue_daemon
                queue_daemon()
            elif choice == '9':
                from integration.queue_poller import main_loop as hub_poller
                hub_poller()
            elif choice == '10':
                submit_notebooklm_from_cli()
            else:
                print(f"{RED}Opção não implementada.{RESET}")
            safe_input("\n[Enter] para continuar...")

if __name__ == "__main__":
    from core.queue_daemon import queue_daemon
    from integration.queue_poller import main_loop as hub_poller
    import argparse
    
    parser = argparse.ArgumentParser(description="HOMES Engine CLI")
    parser.add_argument("--daemon", action="store_true", help="Inicia em modo daemon (Fila local)")
    parser.add_argument("--hub", action="store_true", help="Inicia em modo integração com o Hub")
    parser.add_argument("--brand", default="demo", help="Marca padrão")
    parser.add_argument("--health", action="store_true", help="Checa o VideoLM hospedado")
    parser.add_argument("--manifest", action="store_true", help="Mostra resumo do manifest público")
    parser.add_argument("--demo-url", action="store_true", help="Mostra a URL da demo web")
    parser.add_argument("--render", help="Renderiza um script .txt diretamente")
    parser.add_argument("--demo", action="store_true", help="Renderiza o roteiro demo local pelo Engine")
    parser.add_argument("--notebooklm-submit", action="store_true", help="Submete um video NotebookLM hosted")
    parser.add_argument("--notebooklm-poll", help="Consulta um projectId NotebookLM hosted")
    parser.add_argument("--project-id", default="", help="Project ID para NotebookLM")
    parser.add_argument("--title", default="", help="Título para NotebookLM")
    parser.add_argument("--theme", default="", help="Tema para NotebookLM")
    parser.add_argument("--url", action="append", default=[], help="URL fonte para NotebookLM; pode repetir ou usar vírgulas")
    parser.add_argument("--asset", action="append", default=[], help="Arquivo asset para NotebookLM; pode repetir ou usar vírgulas")
    parser.add_argument("--style", default="paper_craft", choices=NOTEBOOKLM_STYLES, help="Estilo NotebookLM")
    parser.add_argument("--style-prompt", default="", help="Prompt obrigatório quando --style custom")
    parser.add_argument("--live-research", action="store_true", help="Ativa liveResearch no NotebookLM")
    parser.add_argument("--notebook-id", default="", help="NotebookLM notebook existente")
    parser.add_argument("--profile-id", default="default", help="Perfil NotebookLM")
    
    args = parser.parse_args()
    
    if args.health:
        sys.exit(0 if print_health() else 1)
    elif args.manifest:
        sys.exit(0 if print_manifest_summary() else 1)
    elif args.demo_url:
        print_hosted_demo()
    elif args.render:
        sys.exit(0 if render_script(args.render, args.brand) else 1)
    elif args.demo:
        sys.exit(0 if render_script(DEFAULT_DEMO_SCRIPT, args.brand) else 1)
    elif args.notebooklm_submit:
        try:
            submit_notebooklm_from_cli(
                project_id=args.project_id,
                title=args.title,
                theme=args.theme,
                urls=args.url,
                asset_paths=args.asset,
                style=args.style,
                style_prompt=args.style_prompt,
                live_research=args.live_research,
                notebook_id=args.notebook_id,
                profile_id=args.profile_id,
                interactive=False,
            )
        except ValueError as e:
            print(f"{RED}{e}{RESET}")
            sys.exit(2)
    elif args.notebooklm_poll:
        poll_notebooklm_from_cli(args.notebooklm_poll)
    elif args.hub:
        hub_poller()
    elif args.daemon:
        queue_daemon()
    else:
        main()
