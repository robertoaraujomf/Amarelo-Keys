#!/usr/bin/env python3
"""
Teste automatizado dos itens do overlay no editor de texto.
Para cada item salvo em config.json, envia a tecla correspondente para o xed.
"""
import sys
import os
import time
import subprocess
from pathlib import Path

# Adiciona o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

from main import KeySymbol, KeySender, CONFIG_FILE

def get_editor_window():
    """Obtém o ID da janela do xed usando xdotool"""
    try:
        result = subprocess.run(
            ["xdotool", "search", "--name", "xed"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            # Retorna o último ID (janela mais recente)
            ids = result.stdout.strip().split('\n')
            return ids[-1]
    except Exception as e:
        print(f"Erro ao obter janela: {e}")
    return None

def clear_test_file():
    """Limpa o arquivo de teste"""
    with open("/tmp/teste-amarelo.txt", "w") as f:
        f.write("=== Teste Amarelo Keys ===\n\n")
    print("Arquivo de teste limpo.")

def read_test_file():
    """Lê o conteúdo do arquivo de teste"""
    try:
        with open("/tmp/teste-amarelo.txt", "r") as f:
            return f.read()
    except:
        return ""

def main():
    print("=== Iniciando teste automatizado ===\n")
    
    # Carrega itens salvos
    if not CONFIG_FILE.exists():
        print("Arquivo de configuração não encontrado!")
        return
    
    import json
    data = json.loads(CONFIG_FILE.read_text())
    items = [KeySymbol.from_dict(d) for d in data.get("items", [])]
    
    if not items:
        print("Nenhum item salvo no overlay!")
        return
    
    print(f"Encontrados {len(items)} itens para testar:")
    for i, item in enumerate(items):
        print(f"  {i+1}. {item.display} (name={item.name}, xkey={item.xkey})")
    print()
    
    # Limpa arquivo de teste
    clear_test_file()
    
    # Abre o editor de texto
    print("Abrindo editor de texto (xed)...")
    subprocess.Popen(["xed", "/tmp/teste-amarelo.txt"])
    time.sleep(2)
    
    # Obtém ID da janela
    editor_window = get_editor_window()
    if not editor_window:
        print("Não foi possível encontrar a janela do xed!")
        return
    
    print(f"Janela do editor encontrada: {editor_window}\n")
    
    # Cria o KeySender
    sender = KeySender()
    
    # Testa cada item
    for i, item in enumerate(items):
        print(f"Testando {i+1}/{len(items)}: {item.display} (xkey={item.xkey})")
        
        # Foca na janela do editor
        sender.focus_window(editor_window)
        time.sleep(0.2)
        
        # Envia a tecla
        success = sender.send_key(item.xkey or item.name, editor_window)
        
        if success:
            print(f"  ✓ Tecla enviada com sucesso")
        else:
            print(f"  ✗ Erro ao enviar tecla")
        
        time.sleep(0.3)
    
    print("\n=== Teste concluído ===")
    print("Conteúdo do arquivo de teste:")
    print(read_test_file())
    
    # Mantém o editor aberto por alguns segundos
    print("\nO editor permanecerá aberto por 5 segundos para inspeção...")
    time.sleep(5)
    
    # Fecha o editor
    subprocess.run(["pkill", "-f", "xed /tmp/teste-amarelo.txt"])
    print("Editor fechado.")

if __name__ == "__main__":
    main()
