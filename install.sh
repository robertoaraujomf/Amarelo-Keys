#!/bin/bash

set -e

echo "=== Instalando Amarelo Keys ==="

INSTALL_DIR="$HOME/.local/share/amarelo-keys"
mkdir -p "$INSTALL_DIR"

echo "Copiando arquivos..."
cp -r src/* "$INSTALL_DIR/"
cp src/amarelo_keys/__main__.py "$INSTALL_DIR/amarelo_keys/"
cp data/autostart.desktop "$HOME/.config/autostart/amarelo-keys.desktop"

echo "Instalando dependências Python..."
pip3 install --user --break-system-packages pynput pygobject 2>/dev/null || true

echo ""
echo "=== Instalação concluída! ==="
echo ""
echo "Para iniciar manualmente:"
echo "  PYTHONPATH=$INSTALL_DIR python3 -m amarelo_keys --daemon"
echo ""
echo "Para configurar:"
echo "  PYTHONPATH=$INSTALL_DIR python3 -m amarelo_keys --gui"
echo ""
echo "O daemon será iniciado automaticamente no próximo login."
echo ""
echo "Comandos disponíveis:"
echo "  --daemon  : Iniciar como serviço em segundo plano"
echo "  --gui     : Abrir interface de configuração"
echo "  --stop    : Parar o daemon"
echo "  --status  : Verificar status do daemon"
