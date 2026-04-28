#!/usr/bin/env python3
"""
Amarelo Keys - Acessibilidade para Teclas Defeituosas
Instalador e utilitário de configuração
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path

APP_NAME = "Amarelo Keys"
APP_DIR = Path.home() / ".local" / "share" / "amarelo-keys"
DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / "amarelo-keys.desktop"


def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    print("Verificando dependências...")
    
    required = ["python3", "pyqt5"]
    missing = []
    
    for dep in required:
        result = subprocess.run(
            f"python3 -c 'import {dep.replace('python3-', '').replace('pyqt5', 'PyQt5')}'" 
            if dep != "python3" else "python3 --version",
            shell=True, capture_output=True
        )
        if result.returncode != 0:
            missing.append(dep)
    
    if missing:
        print(f"Dependências faltando: {', '.join(missing)}")
        print("\nPara instalar, execute:")
        print(f"  pip3 install PyQt5")
        print(f"  # ou")
        print(f"  sudo apt install python3-pyqt5")
        return False
    
    print("Todas as dependências estão instaladas.")
    return True


def install_xlib():
    """Verifica e instala python-xlib se necessário"""
    try:
        from Xlib import X, XK, display
        print("python-xlib está instalada.")
        return True
    except ImportError:
        print("\npython-xlib não encontrada. Instalando...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "python-xlib"], check=True)
            print("python-xlib instalada com sucesso.")
            return True
        except subprocess.CalledProcessError:
            print("\nErro ao instalar python-xlib.")
            print("Tente executar manualmente:")
            print("  pip3 install python-xlib")
            return False


def setup_autostart():
    """Configura o início automático"""
    desktop_content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Acessibilidade para teclas defeituosas no Linux
Exec={sys.executable} {Path(__file__).resolve()}
Icon=input-keyboard
Terminal=false
Categories=Utility;Accessibility;System;
Keywords=keyboard;accessibility;keys;remap;
"""
    
    try:
        DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DESKTOP_FILE, 'w') as f:
            f.write(desktop_content)
        print(f"Arquivo .desktop criado em: {DESKTOP_FILE}")
        return True
    except Exception as e:
        print(f"Erro ao criar arquivo .desktop: {e}")
        return False


def setup_permissions():
    """Configura as permissões de teclado"""
    print("\n" + "="*50)
    print("CONFIGURAÇÃO DE PERMISSÕES")
    print("="*50)
    
    print("""
Para que o Amarelo Keys funcione corretamente, você precisa
conceder permissão de acesso ao teclado.

OPÇÃO 1: Comando temporário (necessário após cada reinicialização)
--------------------------------------------------------------
Execute no terminal:
    xhost +SI:localuser:root

OPÇÃO 2: Configuração permanente (recomendado)
--------------------------------------------------------------
Adicione seu usuário ao grupo 'input':
    sudo gpasswd -a $USER input
    newgrp input

Após executar um dos comandos acima, reinicie o aplicativo.
""")
    
    response = input("Deseja tentar configurar automaticamente? (s/n): ").strip().lower()
    
    if response == 's':
        try:
            subprocess.run(["xhost", "SI:localuser:root"], check=True)
            print("Permissão configurada com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao configurar permissões: {e}")
            return False
    
    return False


def main():
    print("="*50)
    print(f"{APP_NAME} - Instalador")
    print("="*50)
    print()
    
    if not check_dependencies():
        sys.exit(1)
    
    if not install_xlib():
        sys.exit(1)
    
    print("\nInstalando...")
    setup_autostart()
    
    print("\n" + "="*50)
    print("INSTALAÇÃO CONCLUÍDA")
    print("="*50)
    
    setup_permissions()
    
    print(f"""
Para iniciar o aplicativo, execute:
    python3 {Path(__file__).name}

O aplicativo aparecerá na bandeja do sistema após iniciar.
""")
    
    input("Pressione Enter para sair...")


if __name__ == "__main__":
    main()
