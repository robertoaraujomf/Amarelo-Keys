#!/usr/bin/env python3
"""
Amarelo Keys - Acessibilidade para Teclas Defeituosas
A utility for Linux Mint Cinnamon to remap keys when some keys are defective.
"""

import sys
import os
import json
import subprocess
import time
import threading
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QDialog, QDialogButtonBox, QMessageBox, QGroupBox, QScrollArea,
    QFrame, QLineEdit, QAction, QMenu, QSystemTrayIcon, QStyle,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QPoint
from PyQt5.QtGui import (
    QIcon, QColor, QPalette, QFont, QPainter, QPen, QBrush,
    QKeySequence, QCursor, QPixmap, QGuiApplication, QScreen
)

from Xlib import X, XK, display
from Xlib.ext import xtest


APP_NAME = "Amarelo Keys"
APP_ID = "com.amarelokeys.app"
VERSION = "1.0.0"
CONFIG_DIR = Path.home() / ".config" / "amarelo-keys"
CONFIG_FILE = CONFIG_DIR / "mappings.json"
AUTOSTART_FILE = Path.home() / ".config" / "autostart" / "amarelo-keys.desktop"


class KeySymbols:
    """Key symbols mapping for X11"""
    SPECIAL_KEYS = {
        'Tab': (XK.XK_Tab, 'Tab'),
        'Shift+Tab': (XK.XK_ISO_Left_Tab if hasattr(XK, 'XK_ISO_Left_Tab') else XK.XK_Tab, '⇧Tab'),
        'Enter': (XK.XK_Return, '↵'),
        'Space': (XK.XK_space, '␣'),
        'Escape': (XK.XK_Escape, 'Esc'),
        'Backspace': (XK.XK_BackSpace, '⌫'),
        'Delete': (XK.XK_Delete, 'Del'),
        'Home': (XK.XK_Home, 'Home'),
        'End': (XK.XK_End, 'End'),
        'Page Up': (XK.XK_Page_Up, 'Pg↑'),
        'Page Down': (XK.XK_Page_Down, 'Pg↓'),
        'Insert': (XK.XK_Insert, 'Ins'),
        'Up Arrow': (XK.XK_Up, '↑'),
        'Down Arrow': (XK.XK_Down, '↓'),
        'Left Arrow': (XK.XK_Left, '←'),
        'Right Arrow': (XK.XK_Right, '→'),
        'Pipe (|)': (XK.XK_bar, '|'),
        'Backslash (\\)': (XK.XK_backslash, '\\'),
        'Tilde (~)': (XK.XK_asciitilde, '~'),
        'Backtick (`)': (XK.XK_grave, '`'),
        'Exclamation (!)': (XK.XK_exclam, '!'),
        'At (@)': (XK.XK_at, '@'),
        'Hash (#)': (XK.XK_numbersign, '#'),
        'Dollar ($)': (XK.XK_dollar, '$'),
        'Percent (%)': (XK.XK_percent, '%'),
        'Caret (^)': (XK.XK_asciicircum, '^'),
        'Ampersand (&)': (XK.XK_ampersand, '&'),
        'Asterisk (*)': (XK.XK_asterisk, '*'),
        'Parentheses ()': (XK.XK_parenleft, '('),
        'Minus (-)': (XK.XK_minus, '-'),
        'Plus (+)': (XK.XK_plus, '+'),
        'Equals (=)': (XK.XK_equal, '='),
        'Bracket []': (XK.XK_bracketleft, '['),
        'Brace {}': (XK.XK_braceleft, '{'),
        'Semicolon (;)': (XK.XK_semicolon, ';'),
        'Colon (:)': (XK.XK_colon, ':'),
        'Quote (")': (XK.XK_quotedbl, '"'),
        "Apostrophe (')": (XK.XK_apostrophe, "'"),
        'Less (<)': (XK.XK_less, '<'),
        'Greater (>)': (XK.XK_greater, '>'),
        'Question (?)': (XK.XK_question, '?'),
        'Slash (/)': (XK.XK_slash, '/'),
        'Comma (,)': (XK.XK_comma, ','),
        'Period (.)': (XK.XK_period, '.'),
    }

    MODIFIER_KEYS = {
        'Ctrl': X.ControlMask,
        'Alt': X.Mod1Mask,
        'Shift': X.ShiftMask,
        'Super': X.Mod4Mask,
    }


class GlobalHotkeyListener:
    """Listen for global hotkeys using evdev"""
    
    KEY_NAME_TO_EVDEV = {
        'Insert': 110, 'Home': 102, 'End': 107, 'Delete': 111,
        'Page Up': 104, 'Page Down': 109,
        'Up': 103, 'Down': 108, 'Left': 105, 'Right': 106,
        'F1': 59, 'F2': 60, 'F3': 61, 'F4': 62, 'F5': 63, 'F6': 64,
        'F7': 65, 'F8': 66, 'F9': 67, 'F10': 68, 'F11': 87, 'F12': 88,
        'Print': 99, 'Pause': 119, 'Scroll Lock': 71, 'Num Lock': 76,
        'Tab': 15, 'Escape': 1, 'Return': 28, 'BackSpace': 14,
        'Space': 57, 'Caps Lock': 58, 'Shift': 42, 'Ctrl': 29,
        'Alt': 56, 'Super': 127,
        'A': 30, 'B': 48, 'C': 46, 'D': 32, 'E': 18, 'F': 33, 'G': 34,
        'H': 35, 'I': 23, 'J': 36, 'K': 37, 'L': 38, 'M': 50, 'N': 49,
        'O': 24, 'P': 25, 'Q': 16, 'R': 19, 'S': 31, 'T': 20, 'U': 22,
        'V': 47, 'W': 17, 'X': 45, 'Y': 21, 'Z': 44,
        '0': 11, '1': 2, '2': 3, '3': 4, '4': 5, '5': 6, '6': 7,
        '7': 8, '8': 9, '9': 10,
    }
    
    hotkey_triggered = pyqtSignal(str)
    
    def __init__(self, mappings, callback):
        self.mappings = dict(mappings)
        self.running = True
        self.grabbed_keys = {}
        self._callback = callback
        self._thread = None
        self._lock = threading.Lock()
        self._build_key_map()
    
    def _build_key_map(self):
        """Build mapping of keycodes to evdev codes"""
        STANDARD_MODIFIERS = {'Ctrl', 'Alt', 'Shift', 'Super'}
        SPECIAL_KEYS = {'Insert', 'Delete', 'Home', 'End', 'Page Up', 'Page Down',
                        'Up', 'Down', 'Left', 'Right'}
        
        with self._lock:
            for trigger_key in list(self.mappings.keys()):
                parts = trigger_key.split('+')
                
                modifier_names = []
                key_names = []
                
                for part in parts:
                    if part in STANDARD_MODIFIERS:
                        modifier_names.append(part)
                    elif part in SPECIAL_KEYS:
                        key_names.append(part)
                    else:
                        key_names.append(part)
                
                key_codes = []
                modifiers = []
                
                for mod in modifier_names:
                    if mod == 'Ctrl':
                        modifiers.append('Ctrl')
                    elif mod == 'Alt':
                        modifiers.append('Alt')
                    elif mod == 'Shift':
                        modifiers.append('Shift')
                    elif mod == 'Super':
                        modifiers.append('Super')
                
                for kn in key_names:
                    if kn in self.KEY_NAME_TO_EVDEV:
                        key_codes.append(self.KEY_NAME_TO_EVDEV[kn])
                    else:
                        try:
                            dpy = display.Display()
                            keysym = XK.string_to_keysym(kn)
                            if keysym == 0:
                                keysym = XK.string_to_keysym(kn.capitalize())
                            key_code = dpy.keysym_to_keycode(keysym)
                            if key_code:
                                key_codes.append(key_code)
                            dpy.close()
                        except Exception as e:
                            print(f"Erro ao mapear tecla {kn}: {e}")
                
                if key_codes:
                    self.grabbed_keys[trigger_key] = (key_codes, modifiers)
    
    def update_mappings(self, mappings):
        """Update the key mappings"""
        self.mappings = dict(mappings)
        with self._lock:
            self.grabbed_keys = {}
        self._build_key_map()
    
    def start(self):
        """Start the listener thread"""
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def _run(self):
        """Main thread function"""
        import evdev
        
        keyboard_device = None
        try:
            for path in evdev.list_devices():
                device = evdev.InputDevice(path)
                if 'keyboard' in device.name.lower() or 'AT Translated' in device.name:
                    keyboard_device = device
                    break
            
            if not keyboard_device:
                print("Nenhum dispositivo de teclado encontrado")
                return
            
            try:
                keyboard_device.grab()
            except Exception as e:
                print(f"Não foi possível agarrar o teclado: {e}")
            
            active_modifiers = set()
            active_keys = set()
            triggered_combos = set()
            
            while self.running:
                try:
                    events = keyboard_device.read()
                    for event in events:
                        if event.type == evdev.ecodes.EV_KEY:
                            if event.value == 1:
                                if event.code in [42, 54]:
                                    active_modifiers.add('Shift')
                                elif event.code == 29:
                                    active_modifiers.add('Ctrl')
                                elif event.code == 56:
                                    active_modifiers.add('Alt')
                                elif event.code == 127:
                                    active_modifiers.add('Super')
                                
                                active_keys.add(event.code)
                                
                                with self._lock:
                                    grabbed = dict(self.grabbed_keys)
                                
                                for trigger_key, (codes, mods) in grabbed.items():
                                    if isinstance(codes, list):
                                        required_keys = set(codes)
                                        required_mods = set(mods)
                                        if required_keys <= active_keys and required_mods <= active_modifiers:
                                            if trigger_key not in triggered_combos:
                                                triggered_combos.add(trigger_key)
                                                self.hotkey_triggered.emit(trigger_key)
                                                if self._callback:
                                                    self._callback(trigger_key)
                                    else:
                                        if codes == event.code and set(mods) == active_modifiers:
                                            if trigger_key not in triggered_combos:
                                                triggered_combos.add(trigger_key)
                                                self.hotkey_triggered.emit(trigger_key)
                                                if self._callback:
                                                    self._callback(trigger_key)
                            elif event.value == 0:
                                if event.code in [42, 54]:
                                    active_modifiers.discard('Shift')
                                elif event.code == 54:
                                    active_modifiers.discard('Shift')
                                elif event.code == 29:
                                    active_modifiers.discard('Ctrl')
                                elif event.code == 56:
                                    active_modifiers.discard('Alt')
                                elif event.code == 127:
                                    active_modifiers.discard('Super')
                                
                                active_keys.discard(event.code)
                                
                                for trigger_key, (codes, mods) in list(self.grabbed_keys.items()):
                                    if isinstance(codes, list) and event.code in codes:
                                        triggered_combos.discard(trigger_key)
                except BlockingIOError:
                    time.sleep(0.01)
                except Exception as e:
                    print(f"Erro no loop de eventos: {e}")
                    time.sleep(0.1)
        except Exception as e:
            print(f"Erro no listener: {e}")
        finally:
            if keyboard_device:
                try:
                    keyboard_device.ungrab()
                except Exception:
                    pass
    
    def stop(self):
        """Stop the listener thread"""
        self.running = False
    
    def wait(self, timeout=None):
        """Wait for the thread to finish"""
        if self._thread:
            self._thread.join(timeout)
    
    def isRunning(self):
        """Check if thread is running"""
        return self._thread and self._thread.is_alive()


class KeyboardSimulator:
    """Simulate keyboard input using xdotool (more reliable than XTest)"""
    
    XDOTOOL_AVAILABLE = True
    
    def __init__(self):
        self.dpy = None
        try:
            result = subprocess.run(["xdotool", "version"], capture_output=True, text=True)
            if result.returncode == 0:
                KeyboardSimulator.XDOTOOL_AVAILABLE = True
            else:
                KeyboardSimulator.XDOTOOL_AVAILABLE = False
                self.dpy = display.Display()
        except (subprocess.CalledProcessError, FileNotFoundError):
            KeyboardSimulator.XDOTOOL_AVAILABLE = False
            try:
                self.dpy = display.Display()
            except Exception:
                self.dpy = None
        self._sync_delay = 0.05

    def _get_focused_window(self):
        """Get the window ID of the currently focused window"""
        if self.XDOTOOL_AVAILABLE:
            try:
                result = subprocess.run(
                    ["xdotool", "getactivewindow"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
        return None
    
    def send_key(self, key_name):
        """Send a key event using xdotool to the currently focused window"""
        window_id = self._get_focused_window()
        if window_id:
            subprocess.run(["xdotool", "key", "--window", window_id, key_name], capture_output=True)
        else:
            subprocess.run(["xdotool", "key", "--window", "focus", key_name], capture_output=True)
    
    def send_special_key(self, keysym):
        """Send a special key using its keysym value to the focused window"""
        if self.XDOTOOL_AVAILABLE:
            key_name = self._keysym_to_keyname(keysym)
            if key_name:
                window_id = self._get_focused_window()
                if window_id:
                    subprocess.run(["xdotool", "key", "--window", window_id, key_name], capture_output=True)
                else:
                    subprocess.run(["xdotool", "key", "--window", "focus", key_name], capture_output=True)
        else:
            self._send_keycode_fallback(keysym)
    
    def _keysym_to_keyname(self, keysym):
        """Convert keysym to xdotool key name"""
        KEY_NAME_MAP = {
            XK.XK_Tab: "Tab",
            XK.XK_Return: "Return",
            XK.XK_space: "space",
            XK.XK_Escape: "Escape",
            XK.XK_BackSpace: "BackSpace",
            XK.XK_Delete: "Delete",
            XK.XK_Home: "Home",
            XK.XK_End: "End",
            XK.XK_Page_Up: "Prior",
            XK.XK_Page_Down: "Next",
            XK.XK_Insert: "Insert",
            XK.XK_Up: "Up",
            XK.XK_Down: "Down",
            XK.XK_Left: "Left",
            XK.XK_Right: "Right",
            XK.XK_bar: "bar",
            XK.XK_backslash: "backslash",
            XK.XK_asciitilde: "asciitilde",
            XK.XK_grave: "grave",
            XK.XK_exclam: "exclam",
            XK.XK_at: "at",
            XK.XK_numbersign: "numbersign",
            XK.XK_dollar: "dollar",
            XK.XK_percent: "percent",
            XK.XK_asciicircum: "asciicircum",
            XK.XK_ampersand: "ampersand",
            XK.XK_asterisk: "asterisk",
            XK.XK_parenleft: "parenleft",
            XK.XK_minus: "minus",
            XK.XK_plus: "plus",
            XK.XK_equal: "equal",
            XK.XK_bracketleft: "bracketleft",
            XK.XK_braceright: "braceright",
            XK.XK_semicolon: "semicolon",
            XK.XK_colon: "colon",
            XK.XK_quotedbl: "quotedbl",
            XK.XK_apostrophe: "apostrophe",
            XK.XK_less: "less",
            XK.XK_greater: "greater",
            XK.XK_question: "question",
            XK.XK_slash: "slash",
            XK.XK_comma: "comma",
            XK.XK_period: "period",
        }
        
        if isinstance(keysym, str):
            keysym = getattr(XK, f'XK_{keysym}', None)
        
        return KEY_NAME_MAP.get(keysym)
    
    def _send_keycode_fallback(self, keysym):
        """Fallback method using XTest when xdotool is not available"""
        if self.dpy is None:
            return
            
        if isinstance(keysym, str):
            keysym = XK.string_to_keysym(keysym)
            if keysym == 0:
                keysym = XK.string_to_keysym(keysym.capitalize())
        
        if keysym:
            keycode = self.dpy.keysym_to_keycode(keysym)
            if keycode:
                self.dpy.sync()
                xtest.fake_input(self.dpy, X.KeyPress, keycode)
                self.dpy.flush()
                time.sleep(0.01)
                xtest.fake_input(self.dpy, X.KeyRelease, keycode)
                self.dpy.flush()
    
    def send_character(self, char):
        """Send a single character using xdotool to the currently focused window"""
        window_id = self._get_focused_window()
        
        if self.XDOTOOL_AVAILABLE:
            if char.isupper():
                cmd = ["xdotool", "key", "shift+" + char.lower()]
                if window_id:
                    cmd.insert(2, "--window")
                    cmd.insert(3, window_id)
                subprocess.run(cmd, capture_output=True)
            elif char.islower():
                cmd = ["xdotool", "type", char]
                if window_id:
                    cmd.insert(2, "--window")
                    cmd.insert(3, window_id)
                subprocess.run(cmd, capture_output=True)
            else:
                keysym = XK.string_to_keysym(char)
                if keysym:
                    keyname = self._keysym_to_keyname(keysym)
                    if keyname:
                        cmd = ["xdotool", "key", keyname]
                        if window_id:
                            cmd.insert(2, "--window")
                            cmd.insert(3, window_id)
                        subprocess.run(cmd, capture_output=True)
                    else:
                        cmd = ["xdotool", "type", char]
                        if window_id:
                            cmd.insert(2, "--window")
                            cmd.insert(3, window_id)
                        subprocess.run(cmd, capture_output=True)
            return True
        else:
            keysym = XK.string_to_keysym(char)
            if keysym == 0:
                keysym = XK.string_to_keysym(char.upper())
            if keysym:
                self._send_keycode_fallback(keysym)
                return True
            return False


class ModernButton(QPushButton):
    """Custom styled button with yellow accent"""
    
    def __init__(self, text="", parent=None, primary=False):
        super().__init__(text, parent)
        self.primary = primary
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(36)
        self.setFont(QFont("Segoe UI", 10))
    
    def setPrimary(self, primary):
        self.primary = primary
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        radius = 6
        
        if self.primary:
            color = QColor("#FFD700")
            text_color = QColor("#1a1a2e")
        else:
            color = QColor("#2d3a4f")
            text_color = QColor("#FFD700")
        
        if self.isDown() or self.isChecked():
            color = color.darker(110)
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect.adjusted(0, 0, 0, 0), radius, radius)
        
        painter.setPen(QPen(text_color))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.text())


class MappingItem(QFrame):
    """Widget representing a single key mapping"""
    
    deleted = pyqtSignal(str)
    edit_requested = pyqtSignal(str, str)
    
    def __init__(self, trigger_key, action_key, parent=None):
        super().__init__(parent)
        self.trigger_key = trigger_key
        self.action_key = action_key
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            MappingItem {
                background-color: #1e2a3a;
                border-radius: 8px;
                border: 1px solid #3d4a5c;
                padding: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        trigger_label = QLabel(f"<b style='color: #FFD700;'>{self.trigger_key}</b>")
        trigger_label.setFont(QFont("Segoe UI", 10))
        
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("color: #5a6a7a; font-size: 16px;")
        
        action_label = QLabel(f"<b style='color: #4ecdc4;'>{self.action_key}</b>")
        action_label.setFont(QFont("Segoe UI", 10))
        
        layout.addWidget(trigger_label)
        layout.addWidget(arrow_label)
        layout.addWidget(action_label)
        layout.addStretch()
        
        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(28, 28)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4ecdc4;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(78, 205, 196, 0.2);
                border-radius: 4px;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.trigger_key, self.action_key))
        
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ff6b6b;
                border: none;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 107, 107, 0.2);
                border-radius: 4px;
            }
        """)
        delete_btn.clicked.connect(lambda: self.deleted.emit(self.trigger_key))
        
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)


class SettingsDialog(QDialog):
    """Dialog for adding/editing key mappings"""
    
    def __init__(self, existing_triggers=None, edit_mapping=None, parent=None):
        super().__init__(parent)
        self.existing_triggers = existing_triggers or []
        self.edit_mapping = edit_mapping
        self.selected_trigger = None
        self.selected_action = None
        self._setup_ui()
    
    def _setup_ui(self):
        title = "Editar Mapeamento" if self.edit_mapping else "Adicionar Mapeamento"
        self.setWindowTitle(title)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a2332;
            }
            QLabel {
                color: #e0e0e0;
            }
            QComboBox {
                background-color: #2d3a4f;
                color: #FFD700;
                border: 1px solid #3d4a5c;
                border-radius: 4px;
                padding: 8px;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #FFD700;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        title = QLabel("Configure o atalho de teclado")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFD700;")
        layout.addWidget(title)
        
        trigger_group = QGroupBox("Tecla de Atalho (Gatilho)")
        trigger_group.setStyleSheet("""
            QGroupBox {
                color: #aaa;
                border: 1px solid #3d4a5c;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        trigger_layout = QVBoxLayout()
        
        self.modifier_combo = QComboBox()
        self.modifier_combo.addItems(["Nenhum", "Ctrl", "Alt", "Shift", "Super", "Ctrl+Shift", "Ctrl+Alt"])
        
        self.trigger_key_combo = QComboBox()
        self.trigger_key_combo.addItems(self._get_common_keys())
        
        trigger_inner = QHBoxLayout()
        trigger_inner.addWidget(self.modifier_combo)
        trigger_inner.addWidget(QLabel("+"))
        trigger_inner.addWidget(self.trigger_key_combo)
        trigger_layout.addLayout(trigger_inner)
        trigger_group.setLayout(trigger_layout)
        layout.addWidget(trigger_group)
        
        action_group = QGroupBox("Ação (Caractere/Função)")
        action_group.setStyleSheet("""
            QGroupBox {
                color: #aaa;
                border: 1px solid #3d4a5c;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        action_layout = QVBoxLayout()
        
        self.action_combo = QComboBox()
        self.action_combo.addItems(list(KeySymbols.SPECIAL_KEYS.keys()) + [f"Letra: {chr(i)}" for i in range(ord('a'), ord('z')+1)] + [f"Letra: {chr(i)}" for i in range(ord('A'), ord('Z')+1)] + [f"Número: {i}" for i in range(10)])
        
        action_layout.addWidget(self.action_combo)
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #2d3a4f;
                color: #FFD700;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d4a5f;
            }
        """)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.resize(400, 300)
        
        if self.edit_mapping:
            self._populate_edit_values()
    
    def _get_common_keys(self):
        """Get list of common keys for mapping"""
        return [
            'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
            'Insert', 'Delete', 'Home', 'End', 'Page Up', 'Page Down',
            'Up', 'Down', 'Left', 'Right',
            'Print', 'Pause', 'Scroll Lock', 'Num Lock',
        ]
    
    def _populate_edit_values(self):
        old_trigger, old_action = self.edit_mapping
        parts = old_trigger.split('+')
        if len(parts) > 1:
            modifier = '+'.join(parts[:-1])
            key = parts[-1]
            idx = self.modifier_combo.findText(modifier)
            if idx >= 0:
                self.modifier_combo.setCurrentIndex(idx)
            idx = self.trigger_key_combo.findText(key)
            if idx >= 0:
                self.trigger_key_combo.setCurrentIndex(idx)
        else:
            idx = self.trigger_key_combo.findText(old_trigger)
            if idx >= 0:
                self.trigger_key_combo.setCurrentIndex(idx)
        idx = self.action_combo.findText(old_action)
        if idx >= 0:
            self.action_combo.setCurrentIndex(idx)
    
    def _on_accept(self):
        modifier = self.modifier_combo.currentText()
        key = self.trigger_key_combo.currentText()
        
        if modifier == "Nenhum":
            trigger = key
        else:
            trigger = f"{modifier}+{key}"
        
        action = self.action_combo.currentText()
        
        if trigger in self.existing_triggers and trigger != self.edit_mapping[0]:
            QMessageBox.warning(self, "Aviso", "Este atalho já está mapeado!")
            return
        
        self.selected_trigger = trigger
        self.selected_action = action
        self.accept()
    
    def get_mapping(self):
        return self.selected_trigger, self.selected_action


class PermissionDialog(QDialog):
    """Dialog for requesting keyboard permissions"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("Permissão Necessária")
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a2332;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        icon_label = QLabel("🔑")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label)
        
        title = QLabel("Permissão de Teclado Necessária")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFD700;")
        layout.addWidget(title)
        
        description = QLabel(
            "O Amarelo Keys precisa de permissão para capturar teclas globais.\n\n"
            "Execute o seguinte comando no terminal:"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #ccc; line-height: 1.6;")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        command_box = QLabel()
        command_box.setText("<code style='background: #0d1117; color: #4ecdc4; padding: 10px; border-radius: 4px; display: block;'>"
                           "xhost +SI:localuser:root</code>")
        command_box.setAlignment(Qt.AlignCenter)
        layout.addWidget(command_box)
        
        alt_label = QLabel(
            "Ou adicione seu usuário ao grupo 'input':\n"
            "<code style='color: #4ecdc4;'>sudo gpasswd -a $USER input && newgrp input</code>"
        )
        alt_label.setAlignment(Qt.AlignCenter)
        alt_label.setStyleSheet("color: #888; font-size: 11px;")
        alt_label.setWordWrap(True)
        layout.addWidget(alt_label)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        ok_btn.setText("Abrir Terminal")
        ok_btn.clicked.connect(self._open_terminal)
        
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #2d3a4f;
                color: #FFD700;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #3d4a5f;
            }
        """)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.resize(450, 350)
    
    def _open_terminal(self):
        try:
            subprocess.Popen(["x-terminal-emulator", "-e", "xhost +SI:localuser:root"])
        except Exception:
            try:
                subprocess.Popen(["gnome-terminal", "-e", "xhost +SI:localuser:root"])
            except Exception:
                try:
                    subprocess.Popen(["xfce4-terminal", "-e", "xhost +SI:localuser:root"])
                except Exception:
                    QMessageBox.warning(self, "Erro", "Não foi possível abrir o terminal.")


class MainWindow(QMainWindow):
    """Main application window"""
    
    hotkey_received = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        print("MainWindow: Iniciando...")
        self.mappings = {}
        self.hotkey_listener = None
        print("MainWindow: Criando KeyboardSimulator...")
        self.keyboard_sim = KeyboardSimulator()
        self.tray_icon = None
        print("MainWindow: Setup UI...")
        self._setup_ui()
        print("MainWindow: Load mappings...")
        self._load_mappings()
        print("MainWindow: Setup tray...")
        self._setup_tray()
        print("MainWindow: Start hotkey listener...")
        self._start_hotkey_listener()
        
        self.hotkey_received.connect(self._on_hotkey_received)
        print("MainWindow: Concluído")
    
    def _setup_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setMinimumSize(600, 400)
        self.resize(700, 500)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1621;
            }
            QWidget {
                background-color: #0f1621;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        header = QLabel()
        header.setText(f"<span style='font-size: 24px; font-weight: bold; color: #FFD700;'>⚙</span> "
                      f"<span style='font-size: 24px; font-weight: bold; color: #FFD700;'>{APP_NAME}</span>")
        header.setStyleSheet("padding: 10px 0;")
        main_layout.addWidget(header)
        
        subtitle = QLabel("Mapeie teclas defeituosas para atalhos personalizados")
        subtitle.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 10px;")
        main_layout.addWidget(subtitle)
        
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #151d28;
                border-radius: 12px;
                border: 1px solid #2a3545;
            }
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(16, 16, 16, 16)
        
        mappings_label = QLabel("Mapeamentos Ativos")
        mappings_label.setStyleSheet("color: #aaa; font-size: 13px; font-weight: bold; margin-bottom: 8px;")
        content_layout.addWidget(mappings_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #1e2a3a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d4a5c;
                border-radius: 4px;
            }
        """)
        
        self.mappings_container = QWidget()
        self.mappings_layout = QVBoxLayout(self.mappings_container)
        self.mappings_layout.setSpacing(8)
        self.mappings_layout.setContentsMargins(0, 0, 0, 0)
        self.mappings_layout.addStretch()
        
        scroll.setWidget(self.mappings_container)
        content_layout.addWidget(scroll, 1)
        
        main_layout.addWidget(content_frame, 1)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        add_btn = ModernButton("+ Adicionar Mapeamento", primary=True)
        add_btn.clicked.connect(self._add_mapping)
        buttons_layout.addWidget(add_btn)
        
        refresh_btn = ModernButton("⟳ Reiniciar Listener")
        refresh_btn.clicked.connect(self._restart_listener)
        buttons_layout.addWidget(refresh_btn)
        
        buttons_layout.addStretch()
        
        self.status_label = QLabel("● Ativo")
        self.status_label.setStyleSheet("color: #4ecdc4; font-weight: bold;")
        buttons_layout.addWidget(self.status_label)
        
        main_layout.addLayout(buttons_layout)
    
    def _load_mappings(self):
        """Load mappings from config file"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.mappings = data.get('mappings', {})
            except Exception:
                self.mappings = {}
        self._update_mappings_ui()
    
    def _save_mappings(self):
        """Save mappings to config file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'mappings': self.mappings}, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")
    
    def _update_mappings_ui(self):
        """Update the mappings list in the UI"""
        while self.mappings_layout.count() > 1:
            item = self.mappings_layout.takeAt(0)
            if item.widget() and item.widget() != self.mappings_layout.itemAt(self.mappings_layout.count() - 1).widget():
                item.widget().deleteLater()
        
        for trigger, action in self.mappings.items():
            item = MappingItem(trigger, action)
            item.deleted.connect(self._delete_mapping)
            item.edit_requested.connect(self._edit_mapping)
            self.mappings_layout.insertWidget(self.mappings_layout.count() - 1, item)
    
    def _add_mapping(self):
        """Show dialog to add a new mapping"""
        dialog = SettingsDialog(list(self.mappings.keys()), edit_mapping=None, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            trigger, action = dialog.get_mapping()
            if trigger and action:
                self.mappings[trigger] = action
                self._save_mappings()
                self._update_mappings_ui()
                if self.hotkey_listener:
                    self.hotkey_listener.update_mappings(self.mappings)
    
    def _edit_mapping(self, old_trigger, old_action):
        """Show dialog to edit an existing mapping"""
        dialog = SettingsDialog(list(self.mappings.keys()), (old_trigger, old_action), self)
        if dialog.exec_() == QDialog.Accepted:
            new_trigger, new_action = dialog.get_mapping()
            if new_trigger and new_action:
                del self.mappings[old_trigger]
                self.mappings[new_trigger] = new_action
                self._save_mappings()
                self._update_mappings_ui()
                if self.hotkey_listener:
                    self.hotkey_listener.update_mappings(self.mappings)
    
    def _delete_mapping(self, trigger_key):
        """Delete a mapping"""
        if trigger_key in self.mappings:
            del self.mappings[trigger_key]
            self._save_mappings()
            self._update_mappings_ui()
            if self.hotkey_listener:
                self.hotkey_listener.update_mappings(self.mappings)
    
    def _start_hotkey_listener(self):
        """Start the global hotkey listener"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener.wait()
        
        self.hotkey_listener = GlobalHotkeyListener(self.mappings, self._on_hotkey_pressed)
        self.hotkey_listener.start()
    
    def _restart_listener(self):
        """Restart the hotkey listener"""
        self._start_hotkey_listener()
        self.status_label.setText("● Reiniciado")
        QTimer.singleShot(2000, lambda: self.status_label.setText("● Ativo"))
    
    def _on_hotkey_pressed(self, trigger_key):
        """Handle hotkey press - called from listener thread, use signal for thread safety"""
        self.hotkey_received.emit(trigger_key)
    
    def _on_hotkey_received(self, trigger_key):
        """Handle hotkey received in main thread"""
        if trigger_key in self.mappings:
            action = self.mappings[trigger_key]
            print(f"Hotkey acionado: {trigger_key} -> {action}")
            self._execute_action(action)
    
    def _execute_action(self, action):
        """Execute the mapped action"""
        try:
            if action in KeySymbols.SPECIAL_KEYS:
                keysym = KeySymbols.SPECIAL_KEYS[action][0]
                self.keyboard_sim.send_special_key(keysym)
            elif action.startswith("Letra: "):
                char = action.split(": ")[1]
                self.keyboard_sim.send_character(char)
            elif action.startswith("Número: "):
                num = action.split(": ")[1]
                self.keyboard_sim.send_character(num)
            else:
                self.keyboard_sim.send_character(action)
        except Exception as e:
            print(f"Erro ao executar ação '{action}': {e}")
    
    def _setup_tray(self):
        """Setup system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #1a2332;
                color: #e0e0e0;
                border: 1px solid #3d4a5c;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2d3a4f;
                color: #FFD700;
            }
        """)
        
        open_action = QAction("Abrir Configurações", self)
        open_action.triggered.connect(self._open_settings)
        
        restart_action = QAction("Reiniciar Listener", self)
        restart_action.triggered.connect(self._restart_listener)
        
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self._quit_app)
        
        tray_menu.addAction(open_action)
        tray_menu.addAction(restart_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        self._update_tray_icon()
        self.tray_icon.show()
    
    def _open_settings(self):
        """Show and activate main window"""
        if self.isHidden():
            self.show()
        self.setVisible(True)
        self.raise_()
        self.activateWindow()
        self.raise_()
        QApplication.instance().processEvents()
    
    def _update_tray_icon(self):
        """Update tray icon with colored version"""
        try:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#FFD700")))
            painter.setPen(QPen(QColor("#B8860B"), 2))
            painter.drawEllipse(4, 4, 24, 24)
            painter.setPen(QPen(QColor("#1a1a2e"), 2))
            painter.drawLine(12, 10, 12, 16)
            painter.drawLine(12, 20, 12, 22)
            painter.end()
            self.tray_icon.setIcon(QIcon(pixmap))
        except Exception:
            pass
        self.tray_icon.setToolTip(f"{APP_NAME}\nMapeamentos: {len(self.mappings)}")
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.Trigger:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def _quit_app(self):
        """Quit the application"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener.wait()
        self.tray_icon.hide()
        QApplication.quit()
    
    def closeEvent(self, event):
        """Hide window instead of closing when closing from title bar"""
        event.ignore()
        self.hide()
    
    def customEvent(self, event):
        """Handle custom hotkey events from listener thread"""
        if event.type() == QEvent.User:
            trigger_key = event.text()
            if trigger_key:
                self._on_hotkey_pressed(trigger_key)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and not self.isVisible():
            self._quit_app()
        else:
            super().keyPressEvent(event)


def check_permissions():
    """Check if the application has keyboard permissions"""
    try:
        d = display.Display()
        if d:
            d.close()
            return True
        return False
    except Exception as e:
        print(f"Erro ao verificar permissões: {e}")
        return False


def request_xhost_permission():
    """Try to request xhost permission automatically"""
    try:
        subprocess.run(["xhost", "+SI:localuser:root"], check=True, capture_output=True, timeout=5)
        return True
    except Exception as e:
        print(f"xhost falhou: {e}")
        try:
            subprocess.run(["pkexec", "xhost", "+SI:localuser:root"], check=True, capture_output=True, timeout=10)
            return True
        except Exception as e2:
            print(f"pkexec xhost falhou: {e2}")
            return False


def apply_autostart(enable=True):
    """Enable or disable autostart"""
    if enable:
        AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
        content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Acessibilidade para teclas defeituosas
Exec={sys.executable} {sys.argv[0]}
Icon=preferences-desktop-keyboard
Terminal=false
Categories=Utility;Accessibility;
"""
        try:
            with open(AUTOSTART_FILE, 'w') as f:
                f.write(content)
        except Exception:
            pass
    else:
        try:
            if AUTOSTART_FILE.exists():
                AUTOSTART_FILE.unlink()
        except Exception:
            pass


def main():
    import sys
    sys.stdout.flush()
    print(f"Iniciando {APP_NAME} v{VERSION}...", flush=True)
    
    if not check_permissions():
        print("Tentando obter permissões X...", flush=True)
        if not request_xhost_permission() or not check_permissions():
            app = QApplication(sys.argv)
            dialog = PermissionDialog()
            if dialog.exec_() != QDialog.Accepted:
                print("Usuário recusou dar permissões", flush=True)
                sys.exit(0)
            app.quit()
    
    print("Criando QApplication...", flush=True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    
    stylesheet = """
    QToolTip {
        background-color: #1a2332;
        color: #FFD700;
        border: 1px solid #3d4a5c;
        border-radius: 4px;
        padding: 4px;
    }
    """
    app.setStyleSheet(stylesheet)
    
    print("Criando MainWindow...", flush=True)
    window = MainWindow()
    window.show()
    
    print("Janela principal iniciada", flush=True)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
