#!/bin/bash

# HOMES-Engine Automated Setup for Termux
# Usage: bash setup.sh

set -e

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  🤖 HOMES-ENGINE SETUP (Termux Auto)   ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Update packages
echo -e "${YELLOW}[1/6]${NC} Atualizando repositórios..."
pkg update -y || true

# Step 2: Install Python
echo -e "${YELLOW}[2/6]${NC} Instalando Python 3..."
pkg install -y python3 python-pip || true

# Step 3: Install system dependencies
echo -e "${YELLOW}[3/6]${NC} Instalando FFmpeg e dependências..."
pkg install -y ffmpeg imagemagick || true

# Step 4: Install Termux API (optional but recommended)
echo -e "${YELLOW}[4/6]${NC} Instalando Termux API (opcional)..."
pkg install -y termux-api || echo "  ⚠️  Termux API não disponível (OK)"

# Step 5: Install Python requirements
echo -e "${YELLOW}[5/6]${NC} Instalando dependências Python..."
pip install -r requirements.txt --upgrade

# Step 6: Setup .env
echo -e "${YELLOW}[6/6]${NC} Configurando variáveis de ambiente..."

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ .env criado${NC}"
    echo ""
    echo "⚠️  PRÓXIMO PASSO:"
    echo "   Edite .env e adicione sua GEMINI_API_KEY"
    echo "   nano .env"
else
    echo -e "${GREEN}✅ .env já existe${NC}"
fi

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     ✅ SETUP COMPLETADO COM SUCESSO!   ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Próximos passos:"
echo "  1. Edite .env: nano .env"
echo "  2. Adicione GEMINI_API_KEY"
echo "  3. Execute: python main.py"
echo ""
