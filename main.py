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

_user = os.environ.get("SUDO_USER") or os.environ.get("USER", "root")
USER_HOME = Path(f"/home/{_user}") if _user != "root" else Path("/home/roberto")
CONFIG_DIR = USER_HOME / ".config" / "amarelo-keys"
CONFIG_FILE = CONFIG_DIR / "config.json"
AUTOSTART_FILE = USER_HOME / ".config" / "autostart" / "amarelo-keys.desktop"


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
    KeySymbol("BackTab", "Shift+Tab", keycode=23, modifiers=["Shift"], xkey="ISO_Left_Tab"),
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
    KeySymbol("'", "' Aspas"),
    KeySymbol("\"", "\" Aspas duplas"),
    KeySymbol(",", ", Vírgula"),
    KeySymbol(".", ". Ponto"),
    KeySymbol("/", "/ Barra"),
    KeySymbol("?", "? Interrogação"),
    KeySymbol("<", "< Menor"),
    KeySymbol(">", "> Maior"),
    KeySymbol("_", "_ Underline"),
]

ACENTOS = [
    KeySymbol("á", "á a"),
    KeySymbol("à", "à a"),
    KeySymbol("ã", "ã a"),
    KeySymbol("â", "â a"),
    KeySymbol("Á", "Á A"),
    KeySymbol("À", "À A"),
    KeySymbol("Ã", "Ã A"),
    KeySymbol("Â", "Â A"),
    KeySymbol("é", "é e"),
    KeySymbol("è", "è e"),
    KeySymbol("ê", "ê e"),
    KeySymbol("É", "É E"),
    KeySymbol("È", "È E"),
    KeySymbol("Ê", "Ê E"),
    KeySymbol("í", "í i"),
    KeySymbol("ì", "ì i"),
    KeySymbol("î", "î i"),
    KeySymbol("Í", "Í I"),
    KeySymbol("Ì", "Ì I"),
    KeySymbol("Î", "Î I"),
    KeySymbol("ó", "ó o"),
    KeySymbol("ò", "ò o"),
    KeySymbol("õ", "õ o"),
    KeySymbol("ô", "ô o"),
    KeySymbol("Ó", "Ó O"),
    KeySymbol("Ò", "Ò O"),
    KeySymbol("Õ", "Õ O"),
    KeySymbol("Ô", "Ô O"),
    KeySymbol("ú", "ú u"),
    KeySymbol("ù", "ù u"),
    KeySymbol("û", "û u"),
    KeySymbol("Ú", "Ú U"),
    KeySymbol("Ù", "Ù U"),
    KeySymbol("Û", "Û U"),
    KeySymbol("ç", "ç c"),
    KeySymbol("Ç", "Ç C"),
    KeySymbol("€", "€ Euro"),
    KeySymbol("£", "£ Libra"),
    KeySymbol("°", "° Grau"),
]

CONSOANTS = [
    KeySymbol("b", "b Bê"),
    KeySymbol("c", "c Cê"),
    KeySymbol("d", "d Dê"),
    KeySymbol("f", "f Efe"),
    KeySymbol("g", "g Guê"),
    KeySymbol("h", "h Agá"),
    KeySymbol("j", "j Jelota"),
    KeySymbol("k", "k Cá"),
    KeySymbol("l", "l Ele"),
    KeySymbol("m", "m Emme"),
    KeySymbol("n", "n Enne"),
    KeySymbol("p", "p Pê"),
    KeySymbol("q", "q Queue"),
    KeySymbol("r", "r Ere"),
    KeySymbol("s", "s Ese"),
    KeySymbol("t", "t Tê"),
    KeySymbol("v", "v Ve"),
    KeySymbol("w", "w Duplo vé"),
    KeySymbol("x", "x Éris"),
    KeySymbol("z", "z Zê"),
    KeySymbol("B", "B Bê maiúsculo"),
    KeySymbol("C", "C Cê maiúsculo"),
    KeySymbol("D", "D Dê maiúsculo"),
    KeySymbol("F", "F Efe maiúsculo"),
    KeySymbol("G", "G Guê maiúsculo"),
    KeySymbol("H", "H Agá maiúsculo"),
    KeySymbol("J", "J Jelota maiúsculo"),
    KeySymbol("K", "K Cá maiúsculo"),
    KeySymbol("L", "L Ele maiúsculo"),
    KeySymbol("M", "M Emme maiúsculo"),
    KeySymbol("N", "N Enne maiúsculo"),
    KeySymbol("P", "P Pê maiúsculo"),
    KeySymbol("Q", "Q Queue maiúsculo"),
    KeySymbol("R", "R Ere maiúsculo"),
    KeySymbol("S", "S Ese maiúsculo"),
    KeySymbol("T", "T Tê maiúsculo"),
    KeySymbol("V", "V Ve maiúsculo"),
    KeySymbol("W", "W Duplo vé maiúsculo"),
    KeySymbol("X", "X Éris maiúsculo"),
    KeySymbol("Z", "Z Zê maiúsculo"),
]


def get_all_available():
    all_items = []
    all_items.extend(ACENTOS)
    all_items.extend(CONSOANTS)
    all_items.extend(SPECIAL_CHARS)
    all_items.extend(AVAILABLE_KEYS)
    return all_items


class KeySender:
    SPECIAL_KEYS = {"Tab", "ISO_Left_Tab", "shift+Tab", "Return", "Escape", "space", "BackSpace", "Delete",
                    "Home", "End", "Prior", "Next", "Left", "Right", "Up", "Down",
                    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
                    "Insert", "KP_Enter", "Pause", "Print"}

    def __init__(self):
        self.last_window = None

    def focus_previous_window(self):
        try:
            wid = subprocess.run(
                ["xdotool", "getactivewindow"], 
                capture_output=True, text=True
            ).stdout.strip()
            if wid and wid != str(self.last_window):
                self.last_window = wid
            if wid:
                subprocess.run(["xdotool", "windowactivate", wid], capture_output=True)
                time.sleep(0.1)
                subprocess.run(["xdotool", "mousemove", wid, "100", "100", "click", "1"], capture_output=True)
                time.sleep(0.1)
        except:
            pass

    def send_key(self, xkey, modifiers=None, window_id=None):
        if not xkey:
            return False

        if xkey == "ISO_Left_Tab":
            xkey = "shift+Tab"

        if xkey in KeySender.SPECIAL_KEYS:
            subprocess.run(["xdotool", "key", xkey], capture_output=True)
        else:
            subprocess.run(["xdotool", "type", "--", xkey], capture_output=True)

        return True

    def send_string(self, char):
        os.system(f"xdotool type -- '{char}'")
        return True


class GlobalHotkeyListener(QThread):
    insert_pressed = pyqtSignal()
    key_pressed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.running = True
        self.kbd = None
        self.overlay_active = False
        self._insert_lock = False

    def stop(self):
        self.running = False

    def set_overlay_active(self, active):
        self.overlay_active = active
        self._insert_lock = active

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
                try:
                    for event in kbd.read():
                        if event.type == evdev.ecodes.EV_KEY:
                            if event.value == 1:
                                if event.code == ecodes.KEY_INSERT:
                                    if self._insert_lock:
                                        continue
                                    print("DEBUG: Insert key detected!", flush=True)
                                    self.insert_pressed.emit()
                                    self._insert_lock = True
                                    time.sleep(0.3)
                                    self._insert_lock = False
                                elif self.overlay_active and event.code in (
                                        ecodes.KEY_UP,
                                        ecodes.KEY_DOWN,
                                        ecodes.KEY_ENTER,
                                        ecodes.KEY_KPENTER,
                                        ecodes.KEY_ESC):
                                    self.key_pressed.emit(event.code)
                except (BlockingIOError, OSError):
                    time.sleep(0.05)
                except Exception as e:
                    print(f"Event loop error: {e}", flush=True)
                    time.sleep(0.1)
        finally:
            print("DEBUG: Listener thread stopped", flush=True)


class ConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_items = []
        self.key_sender = KeySender()
        self.hotkey_listener = None
        self.selection_window = None
        self.tray = None


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

        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#FFC107"))
        self.tray.setIcon(QIcon(pixmap))

        menu = QMenu()
        menu.addAction("Abrir Configuração", self.show_config)
        menu.addSeparator()
        menu.addAction("Sair", self.quit_app)
        self.tray.setContextMenu(menu)

        self.tray.show()
        self.tray.activated.connect(self.on_tray_activate)

    def setup_autostart(self):
        app_path = Path(__file__).absolute()
        if not AUTOSTART_FILE.parent.exists():
            AUTOSTART_FILE.parent.mkdir(parents=True)
        if not AUTOSTART_FILE.exists():
            AUTOSTART_FILE.write_text(
                f"[Desktop Entry]\n"
                f"Type=Application\n"
                f"Name={APP_NAME}\n"
                f"Exec=python3 {app_path} --minimized\n"
                f"Hidden=false\n"
                f"NoDisplay=true\n"
                f"X-GNOME-Autostart-enabled=true\n"
            )

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
            self.hotkey_listener.insert_pressed.connect(self.toggle_selection_window)
            self.hotkey_listener.start()

    def toggle_selection_window(self):
        print("DEBUG: toggle_selection_window called", flush=True)
        if self.selection_window and self.selection_window.isVisible():
            print("DEBUG: Hiding existing selection window", flush=True)
            self.selection_window.hide()
            self.on_selection_closed()
        else:
            print("DEBUG: Showing new selection window", flush=True)
            self.update_previous_window()
            self.show_selection_window()

    def update_previous_window(self):
        try:
            self._previous_window = subprocess.run(
                ["xdotool", "getactivewindow"], 
                capture_output=True, text=True
            ).stdout.strip()
        except:
            self._previous_window = None

    def show_selection_window(self):
        print("DEBUG: show_selection_window called", flush=True)
        if not self.selection_window:
            self.selection_window = SelectionWindow(self.selected_items, self.key_sender, self)
            self.selection_window.closed.connect(self.on_selection_closed)
            if self.hotkey_listener:
                self.hotkey_listener.key_pressed.connect(self.selection_window.on_global_key_pressed)
                self.hotkey_listener.set_overlay_active(True)
        self.selection_window.show()

    def on_selection_closed(self):
        if self.hotkey_listener and self.selection_window:
            try:
                self.hotkey_listener.key_pressed.disconnect(self.selection_window.on_global_key_pressed)
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
        if hasattr(self, 'polling_timer'):
            self.polling_timer.stop()
        QApplication.quit()

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
            print(f"EXE: {item.name} xkey={item.xkey}")
            self.hide()
            self.key_sender.send_key(item.xkey or item.name)

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
    window.hide()
    window.start_hotkey_listener()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()