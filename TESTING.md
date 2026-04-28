# Amarelo Keys - Testing Guide

## ⚠️ Current Status

O app está capturando corretamente o teclado em nível evdev. No entanto, **`xdotool` e `UInput` não conseguem injetar eventos em dispositivos que estão grabrados** pelo evdev.

## Como Testar Manualmente

1. **Inicie a app:**
   ```bash
   python3 main.py
   ```

2. **Configure algumas teclas/caracteres:**
   - Clique em "Adicionar" para selecionar itens
   - Clique "OK" para salvar

3. **Teste o Insert key:**
   - Com a app minimizada/rodando
   - **Pressione a tecla INSERT do seu teclado físico**
   - O overlay deveria aparecer
   - Use SETAS para navegar
   - Pressione ENTER para enviar

## Por que os testes automatizados falham

- `xdotool key Insert` funciona apenas em aplicações X11, não no evdev
- `UInput` não consegue injetar em dispositivos grabrados
- Os eventos precisam vir do teclado físico real

## Instalação para Produção

```bash
# Instale como autostart
python3 install.sh

# Ou execute manualmente
python3 main.py --minimized &
```

## Troubleshooting

Se o Insert key não funcionar:
1. Verifique se está no grupo 'input': `groups $USER`
2. Reinicie o X11 se necessário
3. Verifique permissões: `ls -l /dev/input/event*`
