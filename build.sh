#!/usr/bin/env bash
# exit on error
set -o errexit

echo "📦 Instalando dependências Python..."
pip install -r requirements.txt

echo "🎭 Instalando navegadores do Playwright..."
playwright install chromium

echo "📚 Instalando dependências do sistema..."
playwright install-deps chromium

echo "✅ Build concluído com sucesso!"
