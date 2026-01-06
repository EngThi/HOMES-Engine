# 🔗 HOMES-Engine: Contrato de Integração Backend (NestJS)

Este documento define como o backend `ai-video-factory` deve interagir com o `HOMES-Engine`.

## 🚀 Modos de Chamada

O Engine pode ser acionado de três formas principais:

### 1. Via Shell (Pipeline Completo)
Ideal para automações simples ou n8n.
```bash
bash run_full_pipeline.sh "Seu Tema Aqui" "assets/background.mp4" "Cyan_Future"
```
- **Entrada:** String do tema, path do background (opcional), Nome do Tema (opcional).
- **Saída:** Vídeo final em `output/`.

### 2. Via CLI Python (Módulos Core)
O backend pode chamar módulos específicos para processamento granular.

**Gerar Roteiro:**
```bash
python3 core/ai_writer.py --topic "Dicas de Estudo" --out "scripts/roteiro.txt"
```

**Gerar Áudio (Gemini TTS):**
```bash
python3 core/google_tts.py --input "scripts/roteiro.txt" --out "assets/audio/narração.wav"
```

### 3. Via Fila JSON (Recomendado para NestJS)
O Engine monitora a pasta `queue/pending/`. O NestJS deve depositar um arquivo JSON lá.

**Estrutura do JSON (`queue/pending/task_id.json`):**
```json
{
  "task_id": "abc123456",
  "type": "render",
  "priority": 10,
  "data": {
    "topic": "Curiosidades sobre Marte",
    "theme": "yellow_punch",
    "background_video": "assets/background.mp4"
  },
  "created_at": "2026-01-06T15:00:00Z"
}
```

## 📂 Caminhos de Saída

Para integração com o NestJS, o Engine salvará os resultados em:
- **Vídeos:** `output/renders/`
- **Metadata:** `output/metadata_{task_id}.json`

## 📡 Webhooks (n8n)

O `QueueHandler` do Engine está configurado para enviar um POST para o `N8N_WEBHOOK_URL` (definido no `.env`) sempre que uma tarefa for concluída ou falhar.

**Payload de Sucesso:**
```json
{
  "status": "success",
  "task_id": "abc123456",
  "output_path": "/path/to/output/render_final.mp4",
  "duration": 58.5
}
```

---
*Assinado: Homes Architect*
