# 🎥 HOMES Engine - Absolute Cinema Creator

## 🚀 Quick Start

### Termux (Automático)
```bash
bash setup.sh
```

### Manual
```bash
pip install -r requirements.txt
cp .env.example .env
nano .env  # Adicionar GEMINI_API_KEY
python main.py
```

## ✨ Novidades v3.0 (Absolute Cinema)
- **🧠 Modular Architecture:** Motor de IA, TTS e FFmpeg isolados em módulos independentes no `core/`.
- **🎨 Smart Assets:** Geração automática de imagens via **Pollinations.ai (FLUX)** quando o B-Roll é insuficiente.
- **🎬 Professional FFmpeg Engine:** ZoomPan (Ken Burns), standardização de SAR e mixagem inteligente de áudio.
- **🛡️ Audit & Security:** Scripts de verificação de segredos e suporte a variáveis de ambiente centralizadas.
- **📱 Termux Optimized:** Pipeline testado e otimizado para hardware ARM64 com suporte a Voz via Termux API.

### Primeiro uso:
1. Digite ou fale um roteiro
2. Escolha tema
3. Vídeo renderizado em `output/`

---

## 🛠️ O que é o HOMES Engine?

## ✨ Diferenciais Técnicos
- **Custo Zero:** Operação baseada em APIs gratuitas e ambientes mobile (Termux).
- **Integração Termux API:** Entrada de dados via Speech-to-Text e notificações nativas Android.
- **Foco em Retenção:** Geração de prompts otimizados para o nível "Absolute Cinema".

## 🛠️ Stack
- Python 3
- Termux API (System hooks)
- Google Gemini 2.5 Flash (via API externa)

## 🚀 Como Rodar
1. Instale as dependências: `pip install -r requirements.txt`
2. Garanta acesso à Termux API: `pkg install termux-api`
3. Execute: `python main.py`

# 🚀 Participação no Hackatime (Flavortown)

Este repositório faz parte do evento [Flavortown](https://flavortown.hackclub.com/), uma iniciativa incrível do Hack Club para criadores brilhantes testarem ideias inovadoras, explorarem soluções criativas e compartilharem progresso técnico.

💡 **Criado durante o Hackatime**
O projeto foi desenvolvido como parte da competição **Hackatime**, uma maratona dedicada a valorizar o processo criativo e técnico por meio de **devlogs** e **projetos documentados**. A ideia é registrar cada passo do progresso enquanto entregamos soluções reais e experimentamos conceitos novos!

🔗 **Saiba mais sobre o evento**
- [Hackatime no Hack Club](https://hackatime.hackclub.com/)  
- [Flavortown: Conheça iniciativas como esta](https://flavortown.hackclub.com/)  

Nosso objetivo é experimentar, documentar e contribuir abertamente para a comunidade tech! 🎯  
## 🏗️ Architecture v3.0 (Absolute Cinema)

O sistema agora opera em uma arquitetura modular robusta:

1.  **Core Modules (`core/`)**: Lógica isolada para TTS, Vídeo e IA.
2.  **Error Handling**: Sistema de retry automático e fallback de serviços.
3.  **Queue System**: Integração com n8n + Fila Local (JSON) para processamento assíncrono.
4.  **CLI Interface**: Menu interativo com suporte a comandos de voz e pipeline automático.

### 📊 Benchmark Tool

Para testar se seu Termux aguenta o render:

```bash
python3 scripts/benchmark_system.py
```

---

**Desenvolvido com 🤖 + ☕ por Homes Architect**

