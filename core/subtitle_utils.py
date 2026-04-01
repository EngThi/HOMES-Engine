import math
from datetime import timedelta
from typing import List

def format_ass_timestamp(seconds: float) -> str:
    """Converte segundos para formato ASS (H:MM:SS.cc)."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    centis = int(td.microseconds / 10000)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

def generate_ass_from_text(text: str, total_duration: float, output_path: str, font_name="Montserrat ExtraBold", font_size=18):
    """Gera legendas ASS com Word-Level Highlighting (Karaoke Style)."""
    words = text.replace('\n', ' ').split()
    if not words: return False

    header = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 720", "PlayResY: 1280", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,2,0,2,10,10,60,1", ""
    ]

    max_words = 3
    chunks = [words[i:i + max_words] for i in range(0, len(words), max_words)]
    total_chars = sum(len(w) for w in words)
    time_per_char = total_duration / total_chars if total_chars > 0 else 0

    lines = ["[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    current_time = 0.0
    for chunk in chunks:
        chunk_duration = sum(len(w) for w in chunk) * time_per_char
        chunk_start = current_time
        word_start_offset = 0.0
        for i, target_word in enumerate(chunk):
            word_duration = len(target_word) * time_per_char
            event_start = format_ass_timestamp(chunk_start + word_start_offset)
            event_end = format_ass_timestamp(chunk_start + word_start_offset + word_duration)
            styled_text = [f"{{\\c&H00FFFF&}}{w.upper()}{{\\c&HFFFFFF&}}" if i == j else w.upper() for j, w in enumerate(chunk)]
            lines.append(f"Dialogue: 0,{event_start},{event_end},Default,,0,0,0,,{' '.join(styled_text)}")
            word_start_offset += word_duration
        current_time += chunk_duration

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(header + lines))
    return True
