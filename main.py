mport subprocess
import os

def run_command(command):
    return subprocess.check_output(command, shell=True).decode('utf-8').strip()

def main():
    print("🚀 HOMES-ENGINE: INICIANDO SISTEMA...")
    
    # 1. Entrada via Termux API (Voz ou Clipboard)
    print("🎤 Capturando ideia via Speech-to-Text...")
    try:
        tema = run_command("termux-speech-to-text")
    except:
        print("⚠️ Voz não disponível, lendo área de transferência...")
        tema = run_command("termux-clipboard-get")

    if not tema:
        tema = input("Digite o tema manualmente: ")

    # 2. Estrutura de Prompt Detalhado para o Gemini
    prompt_absolute_cinema = f"""
    [DIRETRIZES DE BRANDING HOMES]
    OBJETIVO: Roteiro para vídeo Faceless Evergreen.
    TEMA: {tema}
    ESTÉTICA: Cinematográfica, dinâmica, estilo "Absolute Cinema".
    REQUISITOS: Gancho de retenção nos primeiros 5s, ritmo rápido, sugestões de B-Roll.
    """

    # 3. Persistência de Dados (Modularidade)
    filename = f"scripts/roteiro_{tema.replace(' ', '_')[:10]}.txt"
    os.makedirs("scripts", exist_ok=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(prompt_absolute_cinema)

    # 4. Saída via Notificação e Clipboard
    run_command(f"termux-clipboard-set '{prompt_absolute_cinema}'")
    run_command(f"termux-notification --title 'HOMES: Prompt Gerado' --content 'O roteiro para {tema} está no seu clipboard.'")

    print(f"✅ Sucesso! Arquivo salvo em: {filename}")

if __name__ == "__main__":
    main()
