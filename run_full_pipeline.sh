#!/usr/bin/env bash
# Run full pipeline: topic -> AI script -> VTT subtitles -> TTS audio -> FFmpeg render
# Usage: ./run_full_pipeline.sh "Meu tema aqui" [background.mp4] [ThemeName]
# Requires: python3, ffmpeg, (edge-tts or project Google TTS), fonts in assets/fonts/, assets/background.mp4
set -euo pipefail

TOPIC="${1:-}"
if [ -z "$TOPIC" ]; then
  echo "Uso: $0 \"TEMA\" [background.mp4] [ThemeName]"
  exit 1
fi

BG="${2:-assets/background.mp4}"
THEME="${3:-Cyan_Future}"

SCRIPT_DIR="scripts"
ASSETS_DIR="assets"
AUDIO_DIR="$ASSETS_DIR/audio"
SUBS_DIR="$ASSETS_DIR/subs"
OUT_DIR="output"
FONT_PATH="$ASSETS_DIR/fonts/Montserrat-ExtraBold.ttf"

mkdir -p "$SCRIPT_DIR" "$AUDIO_DIR" "$SUBS_DIR" "$OUT_DIR"

# safe filename
BASE="$(echo "$TOPIC" | tr ' /' '__' | tr -cd '[:alnum:]_-')"
SCRIPT_PATH="$SCRIPT_DIR/roteiro_${BASE}.txt"
AUDIO_PATH="$AUDIO_DIR/${BASE}.wav"
VTT_PATH="$SUBS_DIR/${BASE}.vtt"
OUTPUT_PATH="$OUT_DIR/${BASE}_final.mp4"

echo "=== HOMES-Engine: pipeline start ==="
echo "Tema: $TOPIC"
echo "Background: $BG"
echo "Theme: $THEME"
echo "Script: $SCRIPT_PATH"
echo "Audio: $AUDIO_PATH"
echo "Subtitles: $VTT_PATH"
echo "Output: $OUTPUT_PATH"
echo

# 1) Generate script (AI) if module exists, otherwise fallback to manual prompt via main.py or clipboard
if [ -f "core/ai_writer.py" ]; then
  echo "[1/5] Gerando roteiro com core/ai_writer.py..."
  PYTHONPATH=. python3 core/ai_writer.py --topic "$TOPIC" --out "$SCRIPT_PATH"
else
  echo "[1/5] core/ai_writer.py não encontrado — usando main.py para gerar prompt (fallback)..."
  if [ -f "main.py" ]; then
    # main.py older versions wrote a prompt to clipboard; try writing a prompt file directly
    python3 main.py --topic "$TOPIC" --out "$SCRIPT_PATH" 2>/dev/null || \
      echo -e "TEMA: $TOPIC\n\n(Edite este roteiro manualmente se necessário.)" > "$SCRIPT_PATH"
  else
    echo "Nenhum gerador AI encontrado — criando roteiro placeholder."
    echo -e "TEMA: $TOPIC\n\n(Escreva aqui as falas / legendas.)" > "$SCRIPT_PATH"
  fi
fi
echo "-> Roteiro salvo em $SCRIPT_PATH"
echo

# 3) Generate TTS audio & Subtitles
# Try core/google_tts.py first, then edge-tts. 
# If edge-tts is used, we get accurate subtitles for free.
echo "[3/5] Gerando áudio TTS e Legendas..."
TTS_SUCCESS=false
USED_EDGE_TTS=false

if [ -f "core/google_tts.py" ]; then
  echo "Tentando core/google_tts.py (Gemini TTS)..."
  if PYTHONPATH=. python3 core/google_tts.py --input "$SCRIPT_PATH" --out "$AUDIO_PATH"; then
    TTS_SUCCESS=true
  fi
fi

if [ "$TTS_SUCCESS" = false ] && command -v edge-tts >/dev/null 2>&1; then
  echo "Usando edge-tts (fallback com legendas sincronizadas)..."
  TEXT="$(tr '\n' ' ' < "$SCRIPT_PATH" | sed "s/'/\"/g")"
  # edge-tts generates VTT if we ask nicely. 
  # Note: edge-tts output filename for subs usually appends .vtt, so we might need to move it.
  if edge-tts --voice "pt-BR-AntonioNeural" --text "$TEXT" --write-media "$AUDIO_PATH" --write-subtitles "$VTT_PATH"; then
    TTS_SUCCESS=true
    USED_EDGE_TTS=true
  fi
fi

if [ "$TTS_SUCCESS" = false ]; then
  echo "Nenhum TTS automático disponível. Criando áudio placeholder."
  ffmpeg -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -t 10 -q:a 9 -acodec pcm_s16le "$AUDIO_PATH" -y >/dev/null 2>&1 || true
fi
echo "-> Áudio salvo em $AUDIO_PATH"
echo

# 2) Fallback VTT generation (only if edge-tts wasn't used)
# If we used Gemini or manual, we still need VTT.
if [ "$USED_EDGE_TTS" = false ]; then
  echo "[2/5] Gerando legendas VTT (Estimativa)..."
  python3 - <<PY
import sys
p="$SCRIPT_PATH"
out="$VTT_PATH"
try:
    with open(p, "r", encoding="utf-8") as f:
        lines=[l.strip() for l in f if l.strip()]
except FileNotFoundError:
    lines=["$TOPIC"]
duration_per_line=3.0
with open(out, "w", encoding="utf-8") as fw:
    fw.write("WEBVTT\n\n")
    t=0.0
    for i,l in enumerate(lines):
        start=t
        end=t+duration_per_line
        def fmt2(s):
            h=int(s//3600); m=int((s%3600)//60); sec=s%60
            return f"{h:02d}:{m:02d}:{sec:06.3f}"
        fw.write(f"{fmt2(start)} --> {fmt2(end)}\n{l}\n\n")
        t=end
print('VTT gerado (Estimado):', out)
PY
else
  echo "Legendas geradas via edge-tts (Sincronizadas)."
fi
echo

# 4) Render final video with ffmpeg
# Added -stream_loop -1 to loop background indefinitely until audio ends
echo "[4/5] Renderizando vídeo com FFmpeg..."
if [ ! -f "$BG" ]; then
  echo "AVISO: background não encontrado em $BG — abortando render."
  exit 1
fi

# Build subtitles filter path (escape)
SUBF="$(printf '%s' "$VTT_PATH" | sed "s/'/'\\''/g")"
FONT_ESC="$(printf '%s' "$FONT_PATH" | sed "s/'/'\\''/g")"

ffmpeg -y -stream_loop -1 -i "$BG" -i "$AUDIO_PATH" \
  -vf "scale=1280:720,setsar=1,format=yuv420p,subtitles='$SUBF':force_style='Fontname=Montserrat-ExtraBold,Fontsize=48,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BackColour=&H80000000&,Outline=2,MarginV=40'" \
  -map 0:v:0 -map 1:a:0 -c:v libx264 -preset ultrafast -crf 28 -c:a aac -b:a 128k -shortest "$OUTPUT_PATH"

echo "-> Vídeo final: $OUTPUT_PATH"
echo

# 5) Post: copy to Android download if on Termux
if [ -d "/sdcard" ]; then
  cp "$OUTPUT_PATH" "/sdcard/Download/$(basename "$OUTPUT_PATH")" || true
  echo "Copiado para /sdcard/Download/"
fi

echo "=== Pipeline concluído ==="