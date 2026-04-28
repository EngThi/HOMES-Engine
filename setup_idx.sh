#!/bin/bash
echo "🚀 Iniciando Setup HOMES-Engine v3.0..."

# Criar venv se não existir
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar venv e instalar dependências
echo "📥 Instalando dependências..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Criar pastas básicas
mkdir -p output/renders scripts cache assets/broll branding/demo

# Verificar segredos
if [ ! -f ".env" ]; then
    echo "⚠️  Aviso: .env não encontrado. Copiando do exemplo..."
    cp .env.example .env
fi

echo "✅ Setup concluído! Use 'source venv/bin/activate' para rodar o projeto."
