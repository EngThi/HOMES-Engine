import math
from datetime import timedelta

def format_timestamp(seconds: float) -> str:
    """Converte segundos para formato VTT (HH:MM:SS.mmm)."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

def generate_vtt_from_text(text: str, total_duration: float, output_path: str, max_words_per_line=3):
    """
    Gera um arquivo VTT de alta retenção (Estilo Reels/TikTok).
    Distribui as palavras baseado no peso (quantidade de caracteres) para maior sincronia.
    """
    # Limpeza e tokenização
    words = text.replace('\n', ' ').split()
    if not words:
        return False

    # 1. Agrupar palavras em blocos curtos (Punchy Mode)
    chunks = []
    current_chunk = []
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= max_words_per_line:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # 2. Calcular pesos (duração proporcional ao número de letras)
    total_chars = sum(len(c) for c in chunks)
    time_per_char = total_duration / total_chars if total_chars > 0 else 0

    # 3. Gerar VTT
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        
        current_time = 0.0
        for i, chunk in enumerate(chunks):
            # Duração proporcional ao tamanho do texto no chunk
            chunk_weight = len(chunk)
            duration = chunk_weight * time_per_char
            
            start = current_time
            end = current_time + duration - 0.02 # Pequeno respiro visual
            
            # Garante que o último chunk cubra até o fim exato
            if i == len(chunks) - 1:
                end = total_duration

            f.write(f"{i+1}\n")
            f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
            
            # Adiciona tags de estilo se necessário (ex: Maiúsculo para impacto)
            f.write(f"{chunk.upper()}\n\n")
            
            current_time += duration

    return True
