import subprocess
import os
from video_maker import generate_video

def run_command(command):
    try:
        return subprocess.check_output(command, shell=True).decode('utf-8').strip()
    except:
        return None

def main():
    print("🚀 HOMES-ENGINE: INICIANDO SISTEMA...")
    
    # 1. Entrada via Termux API (Voz ou Clipboard)
    print("🎤 Capturando ideia via Speech-to-Text...")
    tema = run_command("termux-speech-to-text")
    
    if not tema:
        print("⚠️ Voz não disponível, lendo área de transferência...")
        tema = run_command("termux-clipboard-get")

    if not tema or tema == "":
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
    os.makedirs("scripts", exist_ok=True)
    filename = f"scripts/roteiro_{tema.replace(' ', '_')[:10]}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(prompt_absolute_cinema)

    # 4. Saída via Notificação e Clipboard
    run_command(f"termux-clipboard-set '{prompt_absolute_cinema}'")
    run_command(f"termux-notification --title 'HOMES: Prompt Gerado' --content 'O roteiro para {tema} está no seu clipboard.'")

    print(f"✅ Sucesso! Prompt salvo em: {filename}")
    
    # 5. Opção de Renderização Imediata (Modo Rápido)
    decisao = input("\n🎬 Deseja gerar um vídeo de teste com este tema agora? (s/n): ").lower()
    if decisao == 's':
        # Para o vídeo de teste, usamos o tema como conteúdo
        test_script = f"scripts/test_{tema.replace(' ', '_')[:10]}.txt"
        with open(test_script, "w", encoding="utf-8") as f:
            f.write(tema.upper())
        
        generate_video(test_script)
    else:
        print("ℹ️ Para renderizar depois, use: python video_maker.py scripts/seu_roteiro.txt")

if __name__ == "__main__":
    main()
