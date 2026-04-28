import math
from datetime import timedelta
from typing import List

def format_ass_timestamp(seconds: float) -> str:
    """Converte segundos para formato ASS (H:MM:SS.cc)."""
    td = timedelta(seconds=max(0, seconds))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    centis = int(td.microseconds / 10000)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

def generate_ass_from_text(text: str, total_duration: float, output_path: str, brand_colors: dict = None, font_name="Montserrat-ExtraBold", font_size=24, start_offset=0.0):
    """
    Gera legendas ASS Cinematográficas:
    - Word-Level Highlighting (Karaoke)
    - Sombras agressivas e bordas para leitura em qualquer fundo
    - Cores dinâmicas da marca
    """
    words = text.replace('\n', ' ').split()
    if not words: return False

    # Cores (ASS usa formato BGR: &H00BBGGRR)
    primary = "&H00FFFFFF" # Branco
    highlight = "&H0000FFFF" # Amarelo (Destaque)
    outline = "&H00000000"  # Preto (Borda)
    back = "&H64000000"     # Sombra semi-transparente

    if brand_colors:
        if "primary" in brand_colors: primary = brand_colors["primary"]
        if "highlight" in brand_colors: highlight = brand_colors["highlight"]

    header = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 720", "PlayResY: 1280", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]", 
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},{font_size},{primary},{highlight},{outline},{back},1,0,0,0,100,100,0,0,1,3,4,5,30,30,120,1", ""
    ]

    # Lógica de Chunking: 2 a 3 palavras por vez para alta retenção
    max_words_per_screen = 3
    chunks = [words[i:i + max_words_per_screen] for i in range(0, len(words), max_words_per_screen)]
    
    total_chars = sum(len(w) for w in words)
    effective_duration = max(0.1, total_duration - start_offset)
    time_per_char = effective_duration / total_chars

    lines = ["[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    current_time = start_offset

    for chunk in chunks:
        chunk_text = " ".join(chunk).upper()
        chunk_duration = sum(len(w) for w in chunk) * time_per_char
        chunk_start = current_time
        chunk_end = chunk_start + chunk_duration
        
        # Word-Level Timing (Animação de cor na palavra atual)
        word_start_offset = 0.0
        for i, target_word in enumerate(chunk):
            word_duration = len(target_word) * time_per_char
            event_start = format_ass_timestamp(chunk_start + word_start_offset)
            event_end = format_ass_timestamp(chunk_start + word_start_offset + word_duration)
            
            # Cria o efeito de destaque na palavra atual
            styled_parts = []
            for j, w in enumerate(chunk):
                if i == j:
                    # Palavra atual: Cor de destaque + Aumento leve de escala (via tag fscx/fscy)
                    styled_parts.append(f"{{\\c{highlight}\\fscx110\\fscy110}}{w.upper()}{{\\fscx100\\fscy100\\c{primary}}}")
                else:
                    styled_parts.append(w.upper())
            
            lines.append(f"Dialogue: 0,{event_start},{event_end},Default,,0,0,0,,{' '.join(styled_parts)}")
            word_start_offset += word_duration
        
        current_time += chunk_duration

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(header + lines))
    return True
