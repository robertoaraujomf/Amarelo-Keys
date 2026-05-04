#!/usr/bin/env python3
"""
Amarelo Keys - Virtual Keyboard
A virtual keyboard for Linux Mint Cinnamon
"""

import sys
import os
import json
import subprocess
import threading
import time
import atexit
import fcntl
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QDialog, QDialogButtonBox, QMessageBox, QGroupBox, QScrollArea,
    QFrame, QLineEdit, QAction, QMenu, QSystemTrayIcon, QStyle,
    QGraphicsDropShadowEffect, QSizePolicy, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QPoint, QRect
from PyQt5.QtGui import (
    QIcon, QColor, QPalette, QFont, QPainter, QPen, QBrush,
    QKeySequence, QCursor, QPixmap, QGuiApplication, QScreen
)

try:
    import evdev
    from evdev import InputDevice, ecodes
    HAS_EVDEV = True
except ImportError:
    HAS_EVDEV = False
    ecodes = None
    class ecodes:
        KEY_INSERT = 0

APP_NAME = "Amarelo Keys"
VERSION = "1.0.0"

CONFIG_DIR = Path.home() / ".config" / "amarelo-keys"
CONFIG_FILE = CONFIG_DIR / "config.json"
AUTOSTART_FILE = Path.home() / ".config" / "autostart" / "amarelo-keys.desktop"


class KeySymbol:
    def __init__(self, name, display, keycode=None, modifiers=None, xkey=None):
        self.name = name
        self.display = display
        self.keycode = keycode
        self.modifiers = modifiers or []
        self.xkey = xkey or name

    def to_dict(self):
        return {"name": self.name, "display": self.display, "keycode": self.keycode, "modifiers": self.modifiers, "xkey": self.xkey}

    @classmethod
    def from_dict(cls, d):
        name = d.get("name", "")
        display = d.get("display", name)
        keycode = d.get("keycode")
        modifiers = d.get("modifiers", [])
        xkey = d.get("xkey")
        if not xkey:
            xkey = name
        if not keycode or not modifiers:
            for item in get_all_available():
                if item.name == name:
                    keycode = keycode if keycode else item.keycode
                    modifiers = modifiers if modifiers else item.modifiers
                    if not d.get("xkey"):
                        xkey = item.xkey
                    break
        return cls(name, display, keycode, modifiers, xkey)


AVAILABLE_KEYS = [
    KeySymbol("Tab", "Tab", keycode=23, xkey="Tab"),
    KeySymbol("BackTab", "Shift+Tab", keycode=23, modifiers=["Shift"], xkey="shift+Tab"),
    KeySymbol("Enter", "Enter", keycode=36, xkey="Return"),
    KeySymbol("Escape", "Esc", keycode=9, xkey="Escape"),
    KeySymbol("Space", "Espaço", keycode=65, xkey="space"),
    KeySymbol("Backspace", "Backspace", keycode=22, xkey="BackSpace"),
    KeySymbol("Delete", "Delete", keycode=119, xkey="Delete"),
    KeySymbol("Home", "Home", keycode=110, xkey="Home"),
    KeySymbol("End", "End", keycode=115, xkey="End"),
    KeySymbol("PageUp", "Page Up", keycode=112, xkey="Prior"),
    KeySymbol("PageDown", "Page Down", keycode=117, xkey="Next"),
    KeySymbol("Left", "← Esquerda", keycode=113, xkey="Left"),
    KeySymbol("Right", "→ Direita", keycode=114, xkey="Right"),
    KeySymbol("Up", "↑ Acima", keycode=111, xkey="Up"),
    KeySymbol("Down", "↓ Abaixo", keycode=116, xkey="Down"),
    KeySymbol("F1", "F1", keycode=67, xkey="F1"),
    KeySymbol("F2", "F2", keycode=68, xkey="F2"),
    KeySymbol("F3", "F3", keycode=69, xkey="F3"),
    KeySymbol("F4", "F4", keycode=70, xkey="F4"),
    KeySymbol("F5", "F5", keycode=71, xkey="F5"),
    KeySymbol("F6", "F6", keycode=72, xkey="F6"),
    KeySymbol("F7", "F7", keycode=73, xkey="F7"),
    KeySymbol("F8", "F8", keycode=74, xkey="F8"),
    KeySymbol("F9", "F9", keycode=75, xkey="F9"),
    KeySymbol("F10", "F10", keycode=76, xkey="F10"),
    KeySymbol("F11", "F11", keycode=95, xkey="F11"),
    KeySymbol("F12", "F12", keycode=96, xkey="F12"),
]

# Special characters - only symbols, no accented chars, no uppercase distinction
SPECIAL_CHARS = [
    KeySymbol("~", "~ Til"),
    KeySymbol("`", "` Acento"),
    KeySymbol("!", "! Exclamação"),
    KeySymbol("@", "@ Arroba"),
    KeySymbol("#", "# Cerquilha"),
    KeySymbol("$", "$ Cifrão"),
    KeySymbol("%", "% Por cento"),
    KeySymbol("^", "^ Acento"),
    KeySymbol("&", "& E comercial"),
    KeySymbol("*", "* Asterisco"),
    KeySymbol("(", "( Parêntese abre"),
    KeySymbol(")", ") Parêntese fecha"),
    KeySymbol("-", "- Hífen"),
    KeySymbol("+", "+ Mais"),
    KeySymbol("=", "= Igual"),
    KeySymbol("[", "[ Colchete abre"),
    KeySymbol("]", "] Colchete fecha"),
    KeySymbol("{", "{ Chaves abre"),
    KeySymbol("}", "} Chaves fecha"),
    KeySymbol("|", "| Barra vertical"),
    KeySymbol("\\", "\\ Barra invertida"),
    KeySymbol(";", "; Ponto e vírgula"),
    KeySymbol(":", ": Dois pontos"),
    KeySymbol("'", "' Aspas simples"),
    KeySymbol("\"", "\" Aspas duplas"),
    KeySymbol(",", ", Vírgula"),
    KeySymbol(".", ". Ponto"),
    KeySymbol("/", "/ Barra"),
    KeySymbol("?", "? Interrogação"),
    KeySymbol("<", "< Menor"),
    KeySymbol(">", "> Maior"),
    KeySymbol("_", "_ Underline"),
    KeySymbol(" ", "Espaço"),
]

# Only lowercase consonants - uppercase handled by Shift modifier
CONSONANTS = [
    KeySymbol("b", "b"),
    KeySymbol("c", "c"),
    KeySymbol("d", "d"),
    KeySymbol("f", "f"),
    KeySymbol("g", "g"),
    KeySymbol("h", "h"),
    KeySymbol("j", "j"),
    KeySymbol("k", "k"),
    KeySymbol("l", "l"),
    KeySymbol("m", "m"),
    KeySymbol("n", "n"),
    KeySymbol("p", "p"),
    KeySymbol("q", "q"),
    KeySymbol("r", "r"),
    KeySymbol("s", "s"),
    KeySymbol("t", "t"),
    KeySymbol("v", "v"),
    KeySymbol("w", "w"),
    KeySymbol("x", "x"),
    KeySymbol("z", "z"),
]

VOWELS = [
    KeySymbol("a", "a"),
    KeySymbol("e", "e"),
    KeySymbol("i", "i"),
    KeySymbol("o", "o"),
    KeySymbol("u", "u"),
]

NUMBERS = [
    KeySymbol("0", "0"),
    KeySymbol("1", "1"),
    KeySymbol("2", "2"),
    KeySymbol("3", "3"),
    KeySymbol("4", "4"),
    KeySymbol("5", "5"),
    KeySymbol("6", "6"),
    KeySymbol("7", "7"),
    KeySymbol("8", "8"),
    KeySymbol("9", "9"),
]


def get_all_available():
    all_items = []
    all_items.extend(AVAILABLE_KEYS)
    all_items.extend(SPECIAL_CHARS)
    all_items.extend(NUMBERS)
    all_items.extend(VOWELS)
    all_items.extend(CONSONANTS)
    # Sort by display name for cleaner presentation
    all_items.sort(key=lambda x: x.display.lower())
    return all_items


class KeySender:
    SPECIAL_KEYS = {"Tab", "ISO_Left_Tab", "shift+Tab", "Return", "Escape", "space", "BackSpace", "Delete",
                    "Home", "End", "Prior", "Next", "Left", "Right", "Up", "Down",
                    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
                    "Insert", "KP_Enter", "Pause", "Print"}

    def __init__(self):
        self.last_window = None

    def get_active_window(self):
        """Get the currently active window ID"""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    def focus_window(self, window_id):
        """Focus a specific window by ID"""
        if not window_id:
            return False
        try:
            result = subprocess.run(
                ["xdotool", "windowfocus", "--sync", window_id],
                capture_output=True, text=True, timeout=2
            )
            print(f"FOCUS windowfocus: rc={result.returncode}", flush=True)
            time.sleep(0.3)
            return result.returncode == 0
        except Exception as e:
            print(f"FOCUS error: {e}", flush=True)
            return False

    def send_key(self, xkey, window_id=None):
        """Send a key to the specified window or active window"""
        if not xkey:
            return False

        if xkey == "ISO_Left_Tab" or xkey == "shift+Tab":
            xkey = "shift+Tab"

        target_window = window_id or self.get_active_window()

        print(f"SEND: xkey={xkey}, window={target_window}", flush=True)

        try:
            # If we have a target window, focus it first
            if target_window:
                self.focus_window(target_window)

            # Check if the key is a special key
            is_special = (xkey in ["Tab", "shift+Tab", "Return", "Enter", "Escape", "BackSpace",
                                   "Delete", "Home", "End", "Prior", "Next", "Left", "Right",
                                   "Up", "Down", "Insert", "Pause", "Print"] or
                          (len(xkey) >= 2 and xkey.startswith("F") and xkey[1:].isdigit()) or
                          (len(xkey) >= 3 and xkey.startswith("KP_") and xkey[3:].isdigit()))

            if is_special:
                cmd = ["xdotool", "key", "--clearmodifiers", "--delay", "50", xkey]
            else:
                char_to_send = str(xkey).replace('\n', '').replace('\r', '')
                cmd = ["xdotool", "type", "--clearmodifiers", "--delay", "50", "--", char_to_send]

            print(f"SEND cmd: {' '.join(cmd)}", flush=True)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            print(f"SEND result: rc={result.returncode}, stderr={result.stderr.strip()}", flush=True)
            return result.returncode == 0
        except Exception as e:
            print(f"SEND error: {e}", flush=True)
            return False
            return result.returncode == 0
        except Exception as e:
            print(f"SEND error: {e}", flush=True)
            return False


class GlobalHotkeyListener(QThread):
    insert_pressed = pyqtSignal()
    key_pressed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.running = True
        self.kbd = None
        self.overlay_active = False
        self._last_insert_time = 0
        self._last_key_time = 0
        self._keyboard_grabbed = False
        self._grab_lock = threading.Lock()

    def stop(self):
        self.running = False

    def set_overlay_active(self, active):
        with self._grab_lock:
            self.overlay_active = active
            # Also try to grab immediately from main thread for faster response
            if self.kbd:
                try:
                    if active:
                        self.kbd.grab()
                        self._keyboard_grabbed = True
                        print("DEBUG: Keyboard grabbed (from main thread)", flush=True)
                    elif self._keyboard_grabbed:
                        self.kbd.ungrab()
                        self._keyboard_grabbed = False
                        print("DEBUG: Keyboard ungrabbed (from main thread)", flush=True)
                except Exception as e:
                    print(f"DEBUG: immediate grab/ungrab error: {e}", flush=True)

    def run(self):
        print("DEBUG: Listener thread started", flush=True)

        if not HAS_EVDEV:
            print("DEBUG: evdev module is not available", flush=True)
            return

        kbd = None
        paths = list(evdev.list_devices())

        for path in paths:
            try:
                d = InputDevice(path)
                name = d.name.lower()
                if 'keyboard' in name or 'at translated' in name:
                    kbd = d
                    self.kbd = kbd
                    print(f"  -> Selected keyboard: {path} ({d.name})", flush=True)
                    break
            except Exception as e:
                print(f"DEBUG: error opening device {path}: {e}", flush=True)

        if not kbd:
            print("No keyboard device found!", flush=True)
            return

        try:
            try:
                flags = fcntl.fcntl(kbd.fd, fcntl.F_GETFL)
                fcntl.fcntl(kbd.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            except Exception as e:
                print(f"DEBUG: could not set non-blocking mode: {e}", flush=True)

            print("DEBUG: Starting event loop...", flush=True)
            while self.running:
                # Handle keyboard grab/ungrab based on overlay_active state
                with self._grab_lock:
                    should_grab = self.overlay_active
                    already_grabbed = self._keyboard_grabbed

                if should_grab and not already_grabbed:
                    try:
                        kbd.grab()
                        with self._grab_lock:
                            self._keyboard_grabbed = True
                        print("DEBUG: Keyboard grabbed (in thread)", flush=True)
                    except Exception as e:
                        print(f"DEBUG: keyboard grab failed: {e}", flush=True)
                elif not should_grab and already_grabbed:
                    try:
                        kbd.ungrab()
                        with self._grab_lock:
                            self._keyboard_grabbed = False
                        print("DEBUG: Keyboard ungrabbed (in thread)", flush=True)
                    except Exception as e:
                        print(f"DEBUG: keyboard ungrab failed: {e}", flush=True)

                try:
                    for event in kbd.read():
                        if event.type == evdev.ecodes.EV_KEY:
                            if event.value == 1:  # Key press
                                now = time.time()
                                
                                if event.code == ecodes.KEY_INSERT:
                                    if now - self._last_insert_time < 0.5:
                                        continue
                                    self._last_insert_time = now
                                    print("DEBUG: Insert key detected!", flush=True)
                                    self.insert_pressed.emit()
                                
                                elif self.overlay_active:
                                    if event.code in (ecodes.KEY_UP, ecodes.KEY_DOWN,
                                                   ecodes.KEY_ENTER, ecodes.KEY_KPENTER,
                                                   ecodes.KEY_ESC):
                                        self.key_pressed.emit(event.code)
                                        time.sleep(0.05)
                                    # All other keys are consumed by the grab (not forwarded to X)

                    if self.overlay_active:
                        time.sleep(0.02)
                    else:
                        time.sleep(0.05)
                except (BlockingIOError, OSError):
                    time.sleep(0.05)
                except Exception as e:
                    print(f"Event loop error: {e}", flush=True)
                    time.sleep(0.1)
        finally:
            try:
                with self._grab_lock:
                    was_grabbed = self._keyboard_grabbed
                if was_grabbed:
                    kbd.ungrab()
                    print("DEBUG: Keyboard ungrabbed on thread exit", flush=True)
            except:
                pass
            print("DEBUG: Listener thread stopped", flush=True)


class ConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_items = []
        self.key_sender = KeySender()
        self.hotkey_listener = None
        self.selection_window = None
        self.tray = None
        self.load_config()
        self.init_ui()
        self.setup_tray()
        self.setup_autostart()

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} - Configuração")
        # Set window icon
        icon_path = Path(__file__).parent / "app_icon.png"
        if not icon_path.exists():
            icon_path = Path(__file__).parent / "icons" / "amarelo-keys.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(750, 550)
        self.setWindowFlags(Qt.Window)
        self.setStyleSheet("""
            QWidget {
                background-color: #1a2332;
                color: #e0e0e0;
            }
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
                color: #aaa;
            }
            QListWidget {
                background-color: #2d3a4f;
                color: #e0e0e0;
                border: 1px solid #3d4a5c;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #3d4a5f;
                color: #FFD700;
            }
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

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFD700;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Selecione os caracteres e teclas para usar como teclado virtual")
        subtitle.setStyleSheet("color: #aaa;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        splitter = QHBoxLayout()

        left_group = QGroupBox("Caracteres/Teclas Disponíveis")
        left_layout = QVBoxLayout()
        self.available_list = QListWidget()
        self.available_list.setMinimumWidth(280)
        left_layout.addWidget(self.available_list)
        left_group.setLayout(left_layout)
        splitter.addWidget(left_group)

        middle_layout = QVBoxLayout()
        middle_layout.addStretch()
        add_btn = QPushButton("► Adicionar")
        add_btn.clicked.connect(self.add_item)
        middle_layout.addWidget(add_btn)
        remove_btn = QPushButton("◄ Remover")
        remove_btn.clicked.connect(self.remove_item)
        middle_layout.addWidget(remove_btn)
        middle_layout.addStretch()
        splitter.addLayout(middle_layout)

        right_group = QGroupBox("Itens Selecionados")
        right_layout = QVBoxLayout()
        self.selected_list = QListWidget()
        right_layout.addWidget(self.selected_list)
        right_group.setLayout(right_layout)
        splitter.addWidget(right_group)

        layout.addLayout(splitter)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.on_ok)
        btn_layout.addWidget(self.ok_btn)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.update_available_list()
        self.update_selected_list()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip(APP_NAME)

        # Try app_icon.png first (preserves transparency), then tray-icon.png
        icon_path = Path(__file__).parent / "app_icon.png"
        if not icon_path.exists():
            icon_path = Path(__file__).parent / "icons" / "tray-icon.png"
        if icon_path.exists():
            self.tray.setIcon(QIcon(str(icon_path)))
        else:
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor("#FFC107"))
            self.tray.setIcon(QIcon(pixmap))

        menu = QMenu()
        menu.addAction("Abrir Configuração", self.show_config)
        menu.addSeparator()
        menu.addAction("Ajuda", self.show_help)
        menu.addAction("Sobre", self.show_about)
        menu.addSeparator()
        menu.addAction("Sair", self.quit_app)
        self.tray.setContextMenu(menu)

        self.tray.show()
        self.tray.activated.connect(self.on_tray_activate)

    def setup_autostart(self):
        app_path = Path(__file__).absolute()
        AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUTOSTART_FILE.write_text(
            f"[Desktop Entry]\n"
            f"Type=Application\n"
            f"Name={APP_NAME}\n"
            f"Exec={sys.executable} {app_path} --minimized\n"
            f"Hidden=false\n"
            f"NoDisplay=false\n"
            f"X-GNOME-Autostart-enabled=true\n"
            f"Comment=Virtual keyboard for Linux\n"
        )
        print(f"DEBUG: Autostart configured: {AUTOSTART_FILE}", flush=True)

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                self.selected_items = [KeySymbol.from_dict(d) for d in data.get("items", [])]
            except:
                self.selected_items = []
        else:
            self.selected_items = []

    def save_config(self):
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True)
        data = {"items": [item.to_dict() for item in self.selected_items]}
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def update_available_list(self):
        self.available_list.clear()
        all_avail = get_all_available()
        for item in all_avail:
            already = any(s.name == item.name for s in self.selected_items)
            if not already:
                self.available_list.addItem(f"{item.display} ({item.name})")

    def update_selected_list(self):
        self.selected_list.clear()
        for item in self.selected_items:
            self.selected_list.addItem(f"{item.display} ({item.name})")

    def add_item(self):
        current = self.available_list.currentItem()
        if current:
            text = current.text()
            name = text.split(" (")[1].rstrip(")")
            all_avail = get_all_available()
            for item in all_avail:
                if item.name == name and item not in self.selected_items:
                    self.selected_items.append(item)
                    break
            self.update_available_list()
            self.update_selected_list()

    def remove_item(self):
        current = self.selected_list.currentItem()
        if current:
            text = current.text()
            name = text.split(" (")[1].rstrip(")")
            self.selected_items = [s for s in self.selected_items if s.name != name]
            self.update_available_list()
            self.update_selected_list()

    def on_ok(self):
        self.save_config()
        self.hide()
        self.start_hotkey_listener()

    def start_hotkey_listener(self):
        if self.hotkey_listener is None:
            self.hotkey_listener = GlobalHotkeyListener()
            self.hotkey_listener.insert_pressed.connect(self.toggle_selection_window, type=Qt.QueuedConnection)
            self.hotkey_listener.start()

    def toggle_selection_window(self):
        print("DEBUG: toggle_selection_window called", flush=True)
        if self.selection_window and self.selection_window.isVisible():
            print("DEBUG: Hiding existing selection window", flush=True)
            self.selection_window.hide()
            self.on_selection_closed()
        else:
            print("DEBUG: Showing new selection window", flush=True)
            self.show_selection_window()

    def show_selection_window(self):
        print("DEBUG: show_selection_window called", flush=True)
        # Always recreate the selection window to ensure fresh state
        if self.selection_window:
            try:
                self.selection_window.closed.disconnect(self.on_selection_closed)
            except TypeError:
                pass
            self.selection_window.deleteLater()
            self.selection_window = None
        
        # Capture the active window BEFORE showing the overlay
        active_window = self.key_sender.get_active_window()
        print(f"DEBUG: Captured active window: {active_window}", flush=True)
        
        self.selection_window = SelectionWindow(
            self.selected_items, self.key_sender, self
        )
        self.selection_window.target_window = active_window
        self.selection_window.closed.connect(self.on_selection_closed)
        if self.hotkey_listener:
            self.hotkey_listener.key_pressed.connect(self.selection_window.on_global_key_pressed)
            self.hotkey_listener.set_overlay_active(True)
        self.selection_window.show()

    def on_selection_closed(self):
        if self.hotkey_listener:
            try:
                self.hotkey_listener.key_pressed.disconnect()
            except TypeError:
                pass
            # Unset flag to indicate overlay is closed
            self.hotkey_listener.set_overlay_active(False)
        self.selection_window = None

    def show_config(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def on_tray_activate(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_config()
        elif reason == QSystemTrayIcon.Context:
            self.tray.contextMenu().exec_(QCursor.pos())

    def quit_app(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        QApplication.quit()

    def show_help(self):
        help_text = (
            "<b>Como usar o Amarelo Keys:</b><br><br>"
            "1. Abra as configurações pelo menu do tray ou clique duas vezes no ícone.<br>"
            "2. Selecione a tecla defeituosa que deseja mapear.<br>"
            "3. Escolha a tecla de substituição.<br>"
            "4. Clique em 'Adicionar Mapeamento'.<br>"
            "5. O mapeamento será ativado automaticamente.<br><br>"
            "Use o tray icon para acessar rapidamente as configurações ou reiniciar o listener."
        )
        QMessageBox.information(self, "Ajuda - Amarelo Keys", help_text)

    def show_about(self):
        about_text = (
            "<b>Amarelo Keys</b><br><br>"
            "Desenvolvido em 2026<br>"
            f"Versão {VERSION}<br><br>"
            "Por: Roberto Araujo de Moraes Freitas<br>"
            "Contato: robertoaraujomf@gmail.com"
        )
        QMessageBox.about(self, "Sobre - Amarelo Keys", about_text)

    def closeEvent(self, event):
        event.ignore()
        self.hide()


class SelectionWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self, items, key_sender, parent_window=None):
        super().__init__()
        self.items = items
        self.key_sender = key_sender
        self.parent_window = parent_window
        self.current_index = 0
        self.target_window = None

        # Set window flags BEFORE any other operations
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_X11NetWmWindowTypeUtility)
        self.setFocusPolicy(Qt.NoFocus)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Selecione")
        self.setFixedWidth(300)
        self.setStyleSheet("""
            QWidget {
                background-color: #1a2332;
            }
            QListWidget {
                background-color: #2d3a4f;
                color: #e0e0e0;
                border: none;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #FFD700;
                color: #1a2332;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setStyleSheet("""
            background-color: #1a2332;
            border-radius: 8px;
            border: 1px solid #3d4a5c;
        """)
        frame.setGraphicsEffect(QGraphicsDropShadowEffect())
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Selecione uma opção")
        title.setStyleSheet("font-weight: bold; color: #FFD700;")
        frame_layout.addWidget(title)

        self.list_widget = QListWidget()
        for item in self.items:
            self.list_widget.addItem(f"{item.display} ({item.name})")
        self.list_widget.setCurrentRow(0)
        self.list_widget.itemClicked.connect(self.on_item_click)
        frame_layout.addWidget(self.list_widget)

        hint = QLabel("↑↓ Navegar  |  Enter: Enviar  |  Esc: Sair")
        hint.setStyleSheet("color: #5a6a7a; font-size: 10px;")
        frame_layout.addWidget(hint)

        layout.addWidget(frame)

        self.move_to_cursor()

    def move_to_cursor(self):
        cursor = QCursor.pos()
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = cursor.x() - self.width() // 2
            y = cursor.y() - self.height() // 2
            x = max(screen_geo.left(), min(x, screen_geo.right() - self.width()))
            y = max(screen_geo.top(), min(y, screen_geo.bottom() - self.height()))
            self.move(x, y)

    def on_item_click(self, item):
        index = self.list_widget.row(item)
        self.execute_item(index)

    def execute_item(self, index):
        if 0 <= index < len(self.items):
            item = self.items[index]
            print(f"EXE: {item.name} xkey={item.xkey}, target_window={self.target_window}")
            # Hide overlay first
            self.hide()
            # Immediately restore focus to target window
            if self.target_window:
                print(f"RESTORE FOCUS: {self.target_window}", flush=True)
                self.key_sender.focus_window(self.target_window)
            # Use QTimer to delay the key send to prevent Enter key leak
            QTimer.singleShot(500, lambda: self._send_key_after_hide(item))

    def _send_key_after_hide(self, item):
        """Send key after overlay is fully hidden to prevent key leak"""
        print(f"SENDING KEY: {item.xkey or item.name}", flush=True)
        self.key_sender.send_key(item.xkey or item.name, self.target_window)
        self.closed.emit()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Up or (event.modifiers() & Qt.ShiftModifier and key == Qt.Key_Tab):
            self.current_index = max(0, self.current_index - 1)
            self.list_widget.setCurrentRow(self.current_index)
        elif key == Qt.Key_Down:
            self.current_index = min(len(self.items) - 1, self.current_index + 1)
            self.list_widget.setCurrentRow(self.current_index)
        elif key in (Qt.Key_Enter, Qt.Key_Return, 16777221, 16777220):
            self.execute_item(self.current_index)
        elif key == Qt.Key_Escape:
            self.hide()
            self.closed.emit()
        else:
            super().keyPressEvent(event)

    def on_global_key_pressed(self, code):
        if code == 103:  # KEY_UP
            self.current_index = max(0, self.current_index - 1)
            self.list_widget.setCurrentRow(self.current_index)
        elif code == 108:  # KEY_DOWN
            self.current_index = min(len(self.items) - 1, self.current_index + 1)
            self.list_widget.setCurrentRow(self.current_index)
        elif code in (28, 96):  # KEY_ENTER, KEY_KPENTER
            self.execute_item(self.current_index)
        elif code == 1:  # KEY_ESC
            self.hide()
            self.closed.emit()

    def show(self):
        super().show()
        self.current_index = 0
        self.list_widget.setCurrentRow(0)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = ConfigWindow()
    # Check if --minimized flag is passed
    if "--minimized" not in sys.argv:
        window.show()
    else:
        window.hide()
    window.start_hotkey_listener()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()