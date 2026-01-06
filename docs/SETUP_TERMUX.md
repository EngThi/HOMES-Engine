# 📱 HOMES-Engine Setup Guide (Termux)

Guia completo para instalar e usar HOMES-Engine em Termux (Android).

## Pré-requisitos

- Termux instalado (Google Play ou F-Droid)
- Android 7+
- ~2GB espaço disponível
- Conexão internet

## Instalação Rápida (Automática)

### Opção 1: Script Automático (Recomendado)

```bash
cd ~/HOMES-Engine
bash setup.sh
```

**Tempo:** ~5 minutos

### Opção 2: Manual (Didático)

```bash
# Atualizar Termux
pkg update
pkg upgrade -y

# Instalar Python
pkg install python3 python-pip

# Instalar FFmpeg
pkg install ffmpeg

# Clonar repo
cd ~
git clone https://github.com/EngThi/HOMES-Engine.git
cd HOMES-Engine

# Instalar requirements
pip install -r requirements.txt

# Criar .env
cp .env.example .env
```

## Configuração

### 1. Obter Gemini API Key

```
https://aistudio.google.com/app/apikey
```

1. Faça login com Google
2. Crie API key
3. Copie a chave

### 2. Adicionar à .env

```bash
nano .env

# Adicione:
GEMINI_API_KEY=sua_chave_aqui

# Salve: Ctrl+O, Enter, Ctrl+X
```

### 3. Testar Instalação

```bash
python config.py
# Esperado: ✅ Configuração validada!
```

## Primeira Execução

```bash
python main.py

# Menu aparece com 5 opções:
# [1] Gravar Roteiro (Voz)
# [2] Digitar Roteiro (Texto)
# [3] Colar do Clipboard
# [4] Renderizar Arquivo Existente
# [5] Gerar Roteiro (IA Gemini)
# [0] Sair
```

## Troubleshooting

### "command not found: python"
```bash
pkg install python3
which python3  # Verificar
# Às vezes precisa ser: python3
```

### "No module named 'google'"
```bash
pip install google-generativeai
```

### "ffmpeg not found"
```bash
pkg install ffmpeg
```

### "Permission denied: setup.sh"
```bash
chmod +x setup.sh
bash setup.sh
```

## Modo Voz (Termux API)

Para usar Input de Voz:

```bash
pkg install termux-api
# Depois, no app Termux, ative "Draw over other apps"
```

## Saída de Vídeos

Os vídeos processados ficam em:

```
~/HOMES-Engine/output/
```

Para transferir para PC:

```bash
# No seu PC
scp -P 8022 -r user@localhost:~/HOMES-Engine/output ~/Videos/HOMES
```

## Próximas Etapas

- Integração com Backend NestJS
- Deploy em produção
- Integração n8n pra automação
