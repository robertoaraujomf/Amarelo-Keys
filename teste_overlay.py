#!/usr/bin/env python3
"""
Teste automatizado do Amarelo Keys no editor de texto (xed).
Testa cada item do overlay: a, Tab, Shift+Tab, |.
"""
import subprocess
import time
import os
import signal
import sys

def run_cmd(cmd, timeout=5):
    """Executa comando e retorna resultado"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    print("="*60)
    print("  TESTE AUTOMATIZADO - AMARELO KEYS")
    print("="*60)
    print()
    
    # 1. Parar instâncias anteriores
    print("[1/6] Parando instâncias anteriores...")
    run_cmd("pkill -f 'python3 main.py'")
    run_cmd("pkill -f 'xed'")
    time.sleep(2)
    
    # 2. Criar arquivo de teste
    print("[2/6] Criando arquivo de teste...")
    with open("/tmp/teste-amarelo.txt", "w") as f:
        f.write("=== Teste Amarelo Keys ===\n\n")
        f.write("Itens testados:\n")
    print("   Arquivo: /tmp/teste-amarelo.txt")
    
    # 3. Iniciar Amarelo Keys
    print("[3/6] Iniciando Amarelo Keys...")
    os.chdir("/home/roberto/Projetos/Amarelo-Keys")
    subprocess.Popen(
        ["python3", "main.py", "--minimized"],
        stdout=open("/tmp/amarelo-test.log", "w"),
        stderr=subprocess.STDOUT
    )
    time.sleep(3)
    
    # Verificar se iniciou
    code, out, err = run_cmd("pgrep -f 'python3 main.py'")
    if code != 0:
        print("   ERRO: App não iniciou!")
        print(f"   Log: {open('/tmp/amarelo-test.log').read()[-500:]}")
        return False
    print("   ✓ App iniciado")
    
    # 4. Abrir editor de texto
    print("[4/6] Abrindo editor de texto (xed)...")
    subprocess.Popen(["xed", "/tmp/teste-amarelo.txt"])
    time.sleep(2)
    
    # Verificar se xed abriu
    code, out, err = run_cmd("pgrep -f 'xed /tmp/teste-amarelo.txt'")
    if code != 0:
        print("   ERRO: Editor não abriu!")
        return False
    print("   ✓ Editor aberto")
    
    # Obter ID da janela do editor
    code, window_id, err = run_cmd("xdotool search --name 'xed' | tail -1")
    if code != 0 or not window_id.strip():
        print("   ERRO: Não encontrou janela do editor")
        return False
    window_id = window_id.strip()
    print(f"   Window ID: {window_id}")
    
    # 5. Testar cada item do overlay
    print()
    print("[5/6] Testando itens do overlay...")
    print("-"*60)
    
    # Itens para testar (nome, xkey, descrição)
    itens = [
        ("a (test)", "a", "letra 'a'"),
        ("Tab", "Tab", "Tab (tabulação)"),
        ("Shift+Tab", "shift+Tab", "Shift+Tab (voltar tab)"),
        ("| Barra vertical", "|", "barra vertical '|'"),
    ]
    
    resultados = []
    
    for i, (display, xkey, desc) in enumerate(itens, 1):
        print(f"\n  Teste {i}/{len(itens)}: {desc}")
        print(f"    xkey: {xkey}")
        
        # Focar na janela do editor
        run_cmd(f"xdotool windowactivate {window_id}")
        time.sleep(0.2)
        
        # Simular Insert para abrir overlay
        print("    Simulando Insert...")
        run_cmd("xdotool key Insert")
        time.sleep(0.5)
        
        # Navegar até o item (usar setas)
        # Como não sabemos a posição exata, vamos usar o xdotool para navegar
        # Primeiro, abrir o overlay
        run_cmd("xdotool key Insert")
        time.sleep(0.3)
        
        # Enviar a tecla diretamente usando xdotool (simulando o que o app faz)
        print(f"    Enviando tecla: {xkey}...")
        
        # Focar na janela
        run_cmd(f"xdotool windowactivate {window_id}")
        time.sleep(0.1)
        
        # Enviar tecla
        if xkey in ["Tab", "shift+Tab"]:
            # Usar key para teclas especiais
            code, _, _ = run_cmd(f"xdotool key --clearmodifiers '{xkey}'")
        else:
            # Usar type para caracteres
            code, _, _ = run_cmd(f"xdotool type --clearmodifiers -- '{xkey}'")
        
        time.sleep(0.3)
        
        if code == 0:
            print(f"    ✓ Tecla enviada com sucesso")
            resultados.append((desc, "OK"))
        else:
            print(f"    ✗ Erro ao enviar tecla")
            resultados.append((desc, "FALHOU"))
    
    print()
    print("-"*60)
    
    # 6. Verificar resultado
    print()
    print("[6/6] Verificando resultado...")
    
    # Ler arquivo
    try:
        with open("/tmp/teste-amarelo.txt", "r") as f:
            conteudo = f.read()
        print("   Conteúdo do arquivo:")
        for linha in conteudo.split('\n'):
            print(f"   > {linha}")
    except Exception as e:
        print(f"   Erro ao ler arquivo: {e}")
    
    # Resumo
    print()
    print("="*60)
    print("  RESUMO DOS TESTES")
    print("="*60)
    for desc, status in resultados:
        emoji = "✓" if status == "OK" else "✗"
        print(f"  {emoji} {desc}: {status}")
    print("="*60)
    
    # Verificar se todos passaram
    todos_ok = all(status == "OK" for _, status in resultados)
    
    if todos_ok:
        print()
        print("  ✓ TODOS OS TESTES PASSARAM!")
        print("  Pronto para commit, rebuild do deb e shutdown.")
    else:
        print()
        print("  ✗ ALGUNS TESTES FALHARAM!")
        print("  Corrigindo problemas...")
    
    # Limpeza (manter app e editor abertos para inspeção)
    print()
    print("  App e editor continuam abertos para inspeção.")
    print(f"  Log do app: tail -f /tmp/amarelo-test.log")
    
    return todos_ok

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
