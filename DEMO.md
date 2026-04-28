# 🎬 HOMES-Engine × VideoLM — Demo Guide

> Setup completo em um comando. Funciona em qualquer máquina com Docker.

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

## Pré-requisitos

- Docker + Docker Compose
- Git
- Uma chave de API Gemini gratuita: https://aistudio.google.com

---

## Setup em 3 passos

### 1. Clone e configure o VideoLM (motor de renderização)

```bash
git clone https://github.com/EngThi/VideoLM
cd VideoLM
cp .env.example .env
# Edite .env e preencha: GEMINI_API_KEY=sua_chave_aqui
docker-compose up -d
# VideoLM estará rodando em http://localhost:3000
```

### 2. Clone e configure o Engine (orquestrador)

```bash
git clone https://github.com/EngThi/HOMES-Engine
cd HOMES-Engine
cp .env.example .env

# Preencha no .env:
# GEMINI_API_KEY=sua_chave_aqui
# VIDEOLM_URL=http://localhost:3000

bash setup.sh
```

### 3. Gere seu primeiro vídeo

```bash
# Opção A — Menu interativo
python main.py

# Opção B — Linha de comando direto
echo "The reason billionaires wake up at 4am" > queue/my_topic.txt
python core/video_maker.py queue/my_topic.txt

# O .mp4 final aparece em:
# output/renders/HOMES_my_topic_XXXXXX.mp4
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
| `VIDEOLM_URL` | `http://localhost:3000` | URL do backend VideoLM |
| `VIDEOLM_TOKEN` | vazio | JWT VideoLM — vazio usa endpoint `/demo/assemble` |
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
    ↓  POST /api/video/demo/assemble (VideoLM)
    ↓  BullMQ render queue
    ↓  FFmpeg: Ken Burns + SRT subtitles + sidechain music
    ↓  GET /api/video/:id/status  [polling a cada 5s]
    ↓  Download .mp4
 output/renders/HOMES_topic_HHMMSS.mp4
```

---

## Troubleshooting

**`❌ VideoLM rejeitou o job: HTTP 401`**  
O endpoint `/demo/assemble` não existe ainda — adicione-o no VideoLM (ver PR aberto).  
Alternativa: gere um JWT com `POST /api/auth/login` e coloque em `VIDEOLM_TOKEN`.

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
