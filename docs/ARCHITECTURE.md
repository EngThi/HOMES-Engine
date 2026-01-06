# 🏗️ HOMES Engine - Arquitetura do Sistema

O HOMES Engine foi projetado para ser um pipeline de produção de vídeos faceless modular, eficiente e capaz de rodar inteiramente em dispositivos móveis (via Termux).

## 🧩 Componentes Core

### 1. `config.py` (Cérebro de Configuração)
Centraliza todos os caminhos (paths), chaves de API e temas visuais.
- **Hierarquia de Segredos:** `.env` > `.secrets` > Fallback vazio.
- **Automação:** Cria automaticamente as pastas `scripts/`, `output/` e `assets/` se não existirem.

### 2. `core/ai_writer.py` (O Roteirista)
Interface com a API do Google Gemini.
- Recebe um tema e retorna um roteiro otimizado para retenção (gancho, corpo, CTA).
- Utiliza o modelo `gemini-2.5-flash` para velocidade máxima.

### 3. `core/tts_engine.py` (O Narrador)
Utiliza a biblioteca `edge-tts` (Microsoft Azure) para gerar áudio de alta qualidade e legendas sincronizadas (SRT/VTT).
- Suporte a vozes neurais brasileiras (ex: `pt-BR-AntonioNeural`).

### 4. `core/ffmpeg_engine.py` (O Editor de Vídeo)
Isola a complexidade dos comandos FFmpeg.
- **ZoomPan Filter:** Aplica o efeito cinematográfico Ken Burns.
- **Standardization:** Garante que todos os clipes tenham o mesmo SAR (Aspect Ratio) e Pixel Format para evitar erros de concatenação.

### 5. `core/image_gen.py` (Smart Assets)
Integrado ao Pollinations.ai para gerar imagens via modelo **FLUX**.
- Usado como fallback quando não há clips de vídeo (B-Roll) suficientes para o roteiro.

### 6. `core/video_maker.py` (O Diretor)
Orquestra o fluxo de renderização final.
- **Mixagem Inteligente:** Combina narração com música de fundo aplicando *Sidechain Compression* (diminui o volume da música quando há fala).
- **Sequenciamento Dinâmico:** Sorteia clips de `assets/broll/` para criar um vídeo visualmente rico.

## 📁 Estrutura de Pastas

```
HOMES-Engine/
├── core/           # Lógica modular
├── assets/         # Mídias (audio, broll, fonts)
├── scripts/        # Roteiros gerados (.txt)
├── output/         # Resultado final (renders, cache)
├── docs/           # Documentação técnica
├── tests/          # Testes unitários
└── main.py         # Interface CLI Studio
```

## 🛠️ Tecnologias Utilizadas
- **Python 3.12+**
- **FFmpeg 8.0+**
- **Google Gemini API**
- **Edge-TTS**
- **Pollinations.ai API**
- **Termux (Android)**
