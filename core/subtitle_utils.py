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

def generate_vtt_from_text(text: str, total_duration: float, output_path: str, max_chars_per_line=40):
    """
    Gera um arquivo VTT distribuindo o texto uniformemente pela duração do áudio.
    Uma heurística simples para permitir legendas sem timestamps exatos.
    """
    # Limpeza básica e divisão em frases
    words = text.replace('\n', ' ').split()
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 > max_chars_per_line:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += len(word) + 1
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    # Calcular tempo por chunk
    if not chunks:
        return
        
    chunk_duration = total_duration / len(chunks)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        
        current_time = 0.0
        for i, chunk in enumerate(chunks):
            start = current_time
            end = current_time + chunk_duration - 0.05 # Pequeno gap
            
            f.write(f"{i+1}\n")
            f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
            f.write(f"{chunk}\n\n")
            
            current_time += chunk_duration

    return True
