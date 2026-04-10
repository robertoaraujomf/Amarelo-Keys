# Amarelo Keys

Utilitário para Linux Mint Cinnamon que permite remapear teclas de atalho para se comportarem como outras teclas do teclado.

## Objetivo

Auxiliar usuários com teclados defeituosos, permitindo configurar combinações de teclas para enviar caracteres ou comandos diferentes.

## Exemplo de Uso

- `CapsLock + 9` → envia a letra `m`
- `End + 1` → envia `Tab`
- `CapsLock + j` → envia seta para baixo

## Instalação

```bash
chmod +x install.sh
./install.sh
```

Reinicie a sessão para o daemon iniciar automaticamente.

## Uso

```bash
# Iniciar daemon manualmente
python3 -m amarelo_keys --daemon

# Abrir interface de configuração
python3 -m amarelo_keys --gui

# Parar o daemon
python3 -m amarelo_keys --stop

# Verificar status
python3 -m amarelo_keys --status
```

## Configuração

Ao adicionar um mapeamento:
- **Tecla de atalho**: A tecla que você pressiona primeiro (gatilho)
- **Tecla de destino**: A tecla ou combinação que será enviada
- **Desativar original**: Se marcado, a função original da tecla gatilho é desativada

### Exemplos de teclas de destino:
- `m` - letra m minúscula
- `tab` - tecla Tab
- `ctrl+c` - Ctrl+C
- `shift+end` - Shift+End

## Funcionamento

1. O daemon roda em segundo plano capturando todas as teclas
2. Quando você pressiona uma tecla gatilho configurada, ele "segura" a tecla
3. Ao pressionar outra tecla, o daemon envia a(s) tecla(s) de destino configurada(s)
4. A tecla original só é enviada se nenhuma combinação for configurada