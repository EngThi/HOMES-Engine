import math
from datetime import timedelta
from typing import List

def format_ass_timestamp(seconds: float) -> str:
    td = timedelta(seconds=max(0, seconds))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    centis = int(td.microseconds / 10000)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

def generate_ass_from_text(text: str, total_duration: float, output_path: str, font_name="Montserrat ExtraBold", font_size=35, start_offset=1.0):
    """
    v2.4: Legendas Ultra-Impacto (Font 35, Outline 3, Shadow 2).
    Posicionamento otimizado para o terço inferior.
    """
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    if not sentences: return False

    # Alignment=2 (Bottom-Center), MarginV=100 (Um pouco acima da base)
    header = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 720", "PlayResY: 1280", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,3,2,2,30,30,120,1", ""
    ]

    total_chars = sum(len(s) for s in sentences)
    time_per_char = total_duration / total_chars if total_chars > 0 else 0
    lines = ["[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    
    current_time = start_offset
    for sentence in sentences:
        sentence = sentence + "."
        words = sentence.split()
        if not words: continue
        sentence_chars = len(sentence)
        sentence_duration = sentence_chars * time_per_char
        
        # Máximo de 2 palavras por linha para as legendas ficarem GIGANTES sem quebrar
        max_words = 2
        chunks = [words[i:i + max_words] for i in range(0, len(words), max_words)]
        
        chunk_start_time = current_time
        for chunk in chunks:
            chunk_text = " ".join(chunk)
            chunk_chars = len(chunk_text)
            chunk_duration = (chunk_chars / sentence_chars) * sentence_duration
            
            word_start_offset = 0.0
            for i, target_word in enumerate(chunk):
                word_chars = len(target_word)
                word_duration = (word_chars / chunk_chars) * chunk_duration
                event_start = format_ass_timestamp(chunk_start_time + word_start_offset)
                event_end = format_ass_timestamp(chunk_start_time + word_start_offset + word_duration)
                
                styled_text = [f"{{\\c&H00FFFF&}}{w.upper()}{{\\c&HFFFFFF&}}" if i == j else w.upper() for j, w in enumerate(chunk)]
                lines.append(f"Dialogue: 0,{event_start},{event_end},Default,,0,0,0,,{' '.join(styled_text)}")
                word_start_offset += word_duration
            
            chunk_start_time += chunk_duration
        current_time += sentence_duration

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(header + lines))
    return True
