# HOMES-Engine x VideoLM Demo Guide

The reviewer path is hosted first, terminal second.

Hosted demo:

```text
https://54-162-84-165.sslip.io/engine-demo
```

The hosted demo includes pre-rendered videos, deterministic generation, status/progress, and a final MP4 player. The terminal remains the main identity of the project, but reviewers do not need to install the full stack just to see the result.

---

## Arquitetura

```
[HOMES-Engine]  →  gera roteiro, TTS, imagens
      ↓
[VideoLM backend]  →  monta vídeo com FFmpeg (Ken Burns, legendas, música)
      ↓
[Output]  →  .mp4 pronto em output/renders/
```

O Engine é o **orquestrador de conteúdo AI**.  
O VideoLM é o **motor de renderização**.

---

## Reviewer CLI

```bash
python main.py --demo-url
python main.py --health
python main.py --manifest
python main.py
```

Use `python main.py --demo-url` as the fastest handoff. It prints the hosted page backed by the VM renderer.

---

## Local Prerequisites

- Git
- Python 3.10+
- FFmpeg
- Optional Gemini API key for AI script/TTS generation

---

## Local Setup

### 1. Use the hosted VideoLM renderer

```bash
export VIDEOLM_URL=https://54-162-84-165.sslip.io
```

### 2. Clone and configure the Engine

```bash
git clone https://github.com/EngThi/HOMES-Engine
cd HOMES-Engine
cp .env.example .env

bash setup.sh
```

### 3. Run

```bash
python main.py
python main.py --render scripts/e2e_engine_test.txt
```

---

## Verificar conectividade com VideoLM

```bash
python -m core.videolm_client
# Deve mostrar: ✅ VideoLM respondeu! Músicas disponíveis: [...]
```

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `GEMINI_API_KEY` | — | Obrigatória. Gemini TTS + Script + Imagens |
| `VIDEOLM_URL` | `https://54-162-84-165.sslip.io` | URL do backend VideoLM hospedado |
| `VIDEOLM_TOKEN` | vazio | JWT VideoLM opcional, quando o backend exigir autenticação |
| `VIDEOLM_ASSEMBLE_PATH` | auto | Endpoint de render; sem token usa `/api/video/demo/assemble`, com token usa `/api/video/assemble` |
| `VIDEOLM_POLL_INTERVAL` | `5` | Segundos entre checks de status |
| `VIDEOLM_POLL_TIMEOUT` | `600` | Timeout máximo de render (10 min) |
| `POLLINATIONS_API_KEY` | vazio | Opcional — melhora rate limit das imagens |

---

## Pipeline detalhado

```
Script (.txt)
    ↓  Gemini Flash         → roteiro em EN-US
    ↓  Gemini TTS (Kore)    → narration.wav
    ↓  Gemini / Pollinations → scene_0.jpg ... scene_N.jpg  [paralelo, 4 workers]
    ↓  POST /api/video/demo/assemble (demo) ou /api/video/assemble (JWT)
    ↓  BullMQ render queue
    ↓  FFmpeg: Ken Burns + SRT subtitles + sidechain music
    ↓  GET /api/video/:id/status  [polling a cada 5s]
    ↓  Download .mp4 via videoUrl ou videoPath, incluindo URLs relativas como /videos/file.mp4
 output/renders/HOMES_topic_HHMMSS.mp4
```

---

## Troubleshooting

**`❌ VideoLM rejeitou o job: HTTP 401`**  
Gere um JWT com `POST /api/auth/login` e coloque em `VIDEOLM_TOKEN`, ou habilite o endpoint para aceitar o Engine sem autenticação no ambiente de demo.

**`⏰ Timeout aguardando VideoLM`**  
Aumente `VIDEOLM_POLL_TIMEOUT=900` no `.env`. Máquinas lentas podem precisar de mais tempo.

**Imagens saindo 503 da Pollinations**  
A Pollinations tem fila pública. O Engine retenta automaticamente 5x com backoff.  
Se persistir, use a chave VIP: `POLLINATIONS_API_KEY=seu_token`.

---

## Sobre o projeto

HOMES-Engine é parte do ecossistema **HOMES** — uma infraestrutura de automação de conteúdo  
construída para o **Hack Club Flavortown Hackatime**.

- **VideoLM**: https://github.com/EngThi/VideoLM
- **HOMES Hub**: https://github.com/EngThi/HOMES
