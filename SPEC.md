# Amarelo Keys - Specification

## Overview
- **App Name**: Amarelo Keys
- **Type**: Linux Desktop Application (Python/PyQt5)
- **Platform**: Linux Mint Cinnamon
- **Purpose**: Virtual keyboard for sending characters/function keys to any application

## Screens

### 1. Configuration Screen (ConfigScreen)
- **Purpose**: Configure characters and function keys to use in virtual keyboard
- **Components**:
  - Title label: "Amarelo Keys - Configuração"
  - Left panel: Available characters/keys list (scrollable)
  - Right panel: Selected items list (scrollable)
  - Buttons below: Add (>>), Remove (<<), Clear All
  - Bottom buttons: OK, Cancel
- **Behavior**:
  - User selects items from available list
  - Clicks Add to move to selected list
  - Selected items are ordered as they appear in list
  - OK saves configuration and minimizes to tray
  - Cancel discards changes

### 2. System Tray
- **Purpose**: Keep app running in background
- **Components**:
  - Tray icon (yellow key symbol)
  - Context menu: "Abrir Configuração", "Sair"
- **Behavior**:
  - App starts minimized to tray on system boot
  - Left click: Open configuration screen
  - Right click: Show context menu

### 3. Selection Window (SelectionWindow)
- **Purpose**: Show configured characters/keys for selection
- **Components**:
  - Frameless window (appears near cursor or center)
  - Scrollable list with configured items
  - Item format: "[display symbol] - [description]"
- **Behavior**:
  - Appears on Insert key press
  - Closes on Escape key
  - Selected item sends key/character to active app

## Key Features

### Global Hotkey (Insert)
- Listens for Insert key globally (even when app not focused)
- Uses evdev for keyboard capture
- Shows Selection Window when pressed

### Navigation
- ArrowUp: Move selection up
- ArrowDown: Move selection down
- Enter: Execute selected item (send to active app)
- Escape: Close window

### Key Sending (Virtual Keyboard)
- Uses X11 xtest extension to simulate key presses
- Supports regular characters
- Supports function keys (F1-F12)
- Supports special keys (Enter, Tab, Space, Escape, etc.)

### Auto-start
- Creates .desktop entry in ~/.config/autostart/
- Starts minimized to tray on login

## Data Storage
- **Location**: ~/.config/amarelo-keys/
- **File**: config.json
- **Format**:
```json
{
  "items": [
    {"type": "character", "value": "ã"},
    {"type": "character", "value": "ç"},
    {"type": "key", "name": "Enter"},
    {"type": "key", "name": "Tab"}
  ]
}
```

## Dependencies
- Python 3.8+
- python3-pip
- python3-evdev
- python3-xlib
- python3-pyqt5

## Window Behavior
- Selection Window: Shows near cursor position
- Auto-hide after selection (continue listening if more selections needed)
- Only closes on Escape key