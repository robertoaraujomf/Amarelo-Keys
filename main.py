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
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QDialog, QDialogButtonBox, QMessageBox, QGroupBox, QScrollArea,
    QFrame, QLineEdit, QCheckBox, QMenu, QSystemTrayIcon, QStyle,
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

try:
    from Xlib import display, X, XK
    from Xlib.ext import xtest
    HAS_XTEST = True
except ImportError:
    HAS_XTEST = False

APP_NAME = "Amarelo Keys"
VERSION = "1.0.4"

CONFIG_DIR = Path.home() / ".config" / "amarelo-keys"
CONFIG_FILE = CONFIG_DIR / "config.json"
AUTOSTART_FILE = Path.home() / ".config" / "autostart" / "amarelo-keys.desktop"

# Teclas de aderência (sticky keys) e de alternância (toggle keys) do sistema
SYSTEM_STICKY_KEYS = (
    ("org.cinnamon.desktop.a11y.keyboard", "stickykeys-enable"),
    ("org.gnome.desktop.a11y.keyboard", "stickykeys"),
)
SYSTEM_TOGGLE_KEYS = (
    ("org.cinnamon.desktop.a11y.keyboard", "togglekeys-enable"),
)

MODIFIER_NAMES = {
    29: "Ctrl esquerdo",
    97: "Ctrl direito",
    42: "Shift esquerdo",
    54: "Shift direito",
    56: "Alt esquerdo",
    100: "Alt direito",
}



def _gsettings_set(schema, key, value):
    try:
        result = subprocess.run(
            ["gsettings", "set", schema, key, value],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode != 0:
            print(f"DEBUG: gsettings set {schema} {key}={value}: {result.stderr}", flush=True)
        return result.returncode == 0
    except Exception as e:
        print(f"DEBUG: gsettings set {schema} {key}={value}: {e}", flush=True)
    return False

def _gsettings_get(schema, key):
    try:
        result = subprocess.run(
            ["gsettings", "get", schema, key],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip().strip("'")
    except Exception as e:
        print(f"DEBUG: gsettings get {schema} {key}: {e}", flush=True)
    return None


def system_feature_enabled(schemas):
    for schema, key in schemas:
        if _gsettings_get(schema, key) == "true":
            return True
    return False


def system_sticky_enabled():
    """True se as teclas de aderência estiverem habilitadas no sistema"""
    return system_feature_enabled(SYSTEM_STICKY_KEYS)


def system_toggle_enabled():
    """True se as teclas de alternância estiverem habilitadas no sistema"""
    return system_feature_enabled(SYSTEM_TOGGLE_KEYS)
def system_sticky_disable():
    for schema, key in SYSTEM_STICKY_KEYS:
        _gsettings_set(schema, key, "false")


def system_sticky_enable():
    for schema, key in SYSTEM_STICKY_KEYS:
        _gsettings_set(schema, key, "true")


def system_toggle_disable():
    for schema, key in SYSTEM_TOGGLE_KEYS:
        _gsettings_set(schema, key, "false")


def system_toggle_enable():
    for schema, key in SYSTEM_TOGGLE_KEYS:
        _gsettings_set(schema, key, "true")



_SYSTEM_STATE_CACHE = {"time": 0.0, "sticky": False, "toggle": False}


def system_sticky_state(max_age=2.0):
    """(sticky, toggle) do sistema, com cache curto para não poluir com gsettings"""
    now = time.time()
    if now - _SYSTEM_STATE_CACHE["time"] > max_age:
        _SYSTEM_STATE_CACHE["sticky"] = system_sticky_enabled()
        _SYSTEM_STATE_CACHE["toggle"] = system_toggle_enabled()
        _SYSTEM_STATE_CACHE["time"] = now
    return _SYSTEM_STATE_CACHE["sticky"], _SYSTEM_STATE_CACHE["toggle"]


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

    # Keysyms for special characters not resolvable via XK.string_to_keysym
    if HAS_XTEST:
        XCHAR_KEYSYMS = {
            "|": XK.XK_bar, "\\": XK.XK_backslash, "~": XK.XK_asciitilde, "`": XK.XK_grave,
            "!": XK.XK_exclam, "@": XK.XK_at, "#": XK.XK_numbersign, "$": XK.XK_dollar,
            "%": XK.XK_percent, "^": XK.XK_asciicircum, "&": XK.XK_ampersand,
            "*": XK.XK_asterisk, "(": XK.XK_parenleft, ")": XK.XK_parenright,
            "-": XK.XK_minus, "+": XK.XK_plus, "=": XK.XK_equal,
            "[": XK.XK_bracketleft, "]": XK.XK_bracketright,
            "{": XK.XK_braceleft, "}": XK.XK_braceright,
            ";": XK.XK_semicolon, ":": XK.XK_colon,
            "'": XK.XK_apostrophe, '"': XK.XK_quotedbl,
            ",": XK.XK_comma, ".": XK.XK_period, "/": XK.XK_slash,
            "?": XK.XK_question, "<": XK.XK_less, ">": XK.XK_greater,
            "_": XK.XK_underscore, " ": XK.XK_space,
        }
    else:
        XCHAR_KEYSYMS = {}

    def __init__(self):
        self.last_window = None
        self.use_xdotool = shutil.which("xdotool") is not None
        self._dpy = None
        self._mod_keycode_cache = {}
        if HAS_XTEST:
            try:
                self._dpy = display.Display()
            except Exception as e:
                print(f"DEBUG: XTest display init error: {e}", flush=True)
                self._dpy = None
        if self.use_xdotool:
            print("DEBUG: KeySender usando xdotool", flush=True)
        elif HAS_XTEST and self._dpy is not None:
            print("DEBUG: KeySender usando XTest (xdotool ausente)", flush=True)
        else:
            print("DEBUG: KeySender sem backend disponivel", flush=True)

    @property
    def has_xtest(self):
        return HAS_XTEST and self._dpy is not None

    def get_active_window(self):
        """Get the currently active window ID"""
        if self.use_xdotool:
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
        if HAS_XTEST and self._dpy is not None:
            try:
                focus = self._dpy.get_input_focus().focus
                if focus is not None and getattr(focus, "id", None):
                    return str(focus.id)
            except Exception:
                pass
            return None
        return None

    def focus_window(self, window_id):
        """Focus a specific window by ID"""
        if not window_id:
            return False
        if self.use_xdotool:
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
        if HAS_XTEST and self._dpy is not None:
            try:
                win = self._dpy.create_resource_object("window", int(window_id))
                win.set_input_focus(X.RevertToParent, X.CurrentTime)
                self._dpy.flush()
                return True
            except Exception as e:
                print(f"FOCUS error (xtest): {e}", flush=True)
                return False
        return False

    def _xtest_is_special(self, xkey):
        if xkey in ["Tab", "shift+Tab", "ISO_Left_Tab", "Return", "Enter", "Escape", "BackSpace",
                    "Delete", "Home", "End", "Prior", "Next", "Left", "Right",
                    "Up", "Down", "Insert", "Pause", "Print"]:
            return True
        if len(xkey) >= 2 and xkey.startswith("F") and xkey[1:].isdigit():
            return True
        if len(xkey) >= 3 and xkey.startswith("KP_") and xkey[3:].isdigit():
            return True
        return False

    def _xtest_keysym(self, xkey):
        """Resolve an xdotool-style key/char name to an X keysym (0 if unknown)"""
        if xkey == "ISO_Left_Tab":
            return 0x0FE20
        if xkey == "shift+Tab":
            return 0x0FE20
        if xkey == "Enter":
            return XK.XK_Return
        if self._xtest_is_special(xkey):
            return self.XCHAR_KEYSYMS.get(xkey, getattr(XK, f"XK_{xkey}", 0))
        keysym = XK.string_to_keysym(xkey)
        if not keysym:
            keysym = self.XCHAR_KEYSYMS.get(xkey, 0)
        return keysym

    def _xtest_press_keysym(self, keysym):
        """Simulate a key press for an X keysym via XTest, handling required modifiers"""
        d = self._dpy
        if d is None or not keysym:
            return False
        pairs = list(d.keysym_to_keycodes(keysym))
        if not pairs:
            return False
        keycode, index = min(pairs, key=lambda p: p[1])

        modifiers = []
        if index in (1, 3, 5, 7):
            modifiers.append(XK.XK_Shift_L)
        if index in (2, 3, 6, 7):
            modifiers.append(0xFF7E)  # Mode_switch
        if index in (4, 5, 6, 7):
            modifiers.append(0xFE03)  # ISO_Level3_Shift

        mod_keycodes = []
        for mod_sym in modifiers:
            mkc = d.keysym_to_keycode(mod_sym)
            if not mkc:
                return False
            mod_keycodes.append(mkc)

        try:
            for mkc in mod_keycodes:
                xtest.fake_input(d, X.KeyPress, mkc)
            xtest.fake_input(d, X.KeyPress, keycode)
            xtest.fake_input(d, X.KeyRelease, keycode)
            for mkc in mod_keycodes:
                xtest.fake_input(d, X.KeyRelease, mkc)
            d.flush()
        except Exception as e:
            print(f"SEND error (xtest): {e}", flush=True)
            return False
        time.sleep(0.05)
        return True

    def _xtest_modifier_keycode(self, code):
        """Return the X keycode used to synthesize a held modifier for an evdev code (0 if unavailable)"""
        if not self.has_xtest:
            return 0
        if code in self._mod_keycode_cache:
            return self._mod_keycode_cache[code]
        syms = {
            29: XK.XK_Control_L, 97: XK.XK_Control_R,
            42: XK.XK_Shift_L, 54: XK.XK_Shift_R,
            56: XK.XK_Alt_L, 100: XK.XK_Alt_R,
        }
        sym = syms.get(code, 0)
        kc = 0
        if sym:
            kc = self._dpy.keysym_to_keycode(sym)
            if not kc and sym == XK.XK_Alt_R:
                kc = self._dpy.keysym_to_keycode(0xFE03)  # AltGr (ISO_Level3_Shift)
        self._mod_keycode_cache[code] = kc
        return kc

    def xtest_modifier_press(self, code):
        """Synthesize a held modifier press for an evdev modifier code via XTest"""
        if not self.has_xtest:
            return False
        kc = self._xtest_modifier_keycode(code)
        if not kc:
            return False
        try:
            xtest.fake_input(self._dpy, X.KeyPress, kc)
            self._dpy.flush()
            return True
        except Exception as e:
            print(f"SEND error (sticky press): {e}", flush=True)
            return False

    def xtest_modifier_release(self, code):
        """Release a synthesized modifier for an evdev modifier code via XTest"""
        if not self.has_xtest:
            return False
        kc = self._xtest_modifier_keycode(code)
        if not kc:
            return False
        try:
            xtest.fake_input(self._dpy, X.KeyRelease, kc)
            self._dpy.flush()
            return True
        except Exception as e:
            print(f"SEND error (sticky release): {e}", flush=True)
            return False

    def _send_key_xtest(self, xkey):
        """Send a key using XTest (python-xlib) when xdotool is not available"""
        keysym = self._xtest_keysym(xkey)
        if not keysym:
            print(f"SEND no keysym for: {xkey}", flush=True)
            return False
        print(f"SEND (xtest): xkey={xkey}, keysym={hex(keysym)}", flush=True)
        return self._xtest_press_keysym(keysym)

    def send_key(self, xkey, window_id=None):
        """Send a key to the specified window or active window"""
        if not xkey:
            return False

        if not self.use_xdotool:
            return self._send_key_xtest(xkey)

        if xkey == "ISO_Left_Tab" or xkey == "shift+Tab":
            xkey = "shift+Tab"

        target_window = window_id or self.get_active_window()

        print(f"SEND: xkey={xkey}, window={target_window}", flush=True)

        try:
            # If we have a target window, focus it first
            if target_window:
                self.focus_window(target_window)

            # Check if the key is a special key
            is_special = self._xtest_is_special(xkey)

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


class GlobalHotkeyListener(QThread):
    insert_pressed = pyqtSignal()
    key_pressed = pyqtSignal(int)
    modifiers_changed = pyqtSignal(list)

    # evdev codes of modifier keys that can be latched (teclas de aderência)
    STICKY_MODIFIER_CODES = {29, 97, 42, 54, 56, 100}

    def __init__(self):
        super().__init__()
        self.running = True
        self.kbd = None
        self.overlay_active = False
        self._last_insert_time = 0
        self._last_key_time = 0
        self._keyboard_grabbed = False
        self._grab_lock = threading.Lock()
        self.sticky_enabled = False
        self.key_sender = None
        self._sticky_latched = set()
        self._sticky_phys_down = set()
        self._sticky_typed_while_mod = set()
        self._sticky_release_on_next = False
        self._sticky_release_pending = False
        self._sticky_reset_pending = False
        self._sticky_lock = threading.Lock()
        self._last_reported_modifiers = ()

    def stop(self):
        self.running = False
        self._sticky_release_pending = True

    def set_sticky_enabled(self, enabled):
        self.sticky_enabled = bool(enabled)
        if not self.sticky_enabled:
            self._sticky_release_pending = True

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
        self._sticky_release_pending = True
        self._sticky_reset_pending = True

    def _release_sticky_latches(self):
        if not self.key_sender:
            return
        with self._sticky_lock:
            latched = list(self._sticky_latched)
            self._sticky_latched.clear()
        for code in latched:
            try:
                self.key_sender.xtest_modifier_release(code)
            except Exception:
                pass

    def pressed_modifiers(self):
        """Modifier keys the system currently reports as pressed (evdev state)"""
        codes = set()
        with self._sticky_lock:
            codes.update(self._sticky_phys_down)
            codes.update(self._sticky_latched)
        if self.kbd:
            try:
                active = self.kbd.active_keys
                if callable(active):
                    active = active()
                codes.update(c for c in active if c in self.STICKY_MODIFIER_CODES)
            except Exception as e:
                print(f"DEBUG: could not read active keys: {e}", flush=True)
        return sorted(codes)

    def release_pressed_modifiers(self):
        """Force the release of modifier keys that the system still sees as pressed"""
        codes = self.pressed_modifiers()
        with self._sticky_lock:
            self._sticky_latched.clear()
            self._sticky_typed_while_mod.clear()
            self._sticky_release_on_next = False
            # marks keys whose physical release must not latch again
            self._sticky_typed_while_mod.update(codes)
        if self.key_sender:
            for code in codes:
                self.key_sender.xtest_modifier_release(code)
        print(f"DEBUG: modificadoras liberadas: {codes}", flush=True)
        self._emit_modifiers()
        return codes

    def _emit_modifiers(self):
        codes = self.pressed_modifiers()
        if codes == self._last_reported_modifiers:
            return
        self._last_reported_modifiers = codes
        self.modifiers_changed.emit(codes)

    def _handle_sticky_event(self, code, value):
        """Track modifier presses, latch them (sticky keys) and report state"""
        if code not in self.STICKY_MODIFIER_CODES:
            if not self.sticky_enabled or self.overlay_active:
                return
            if value == 1:  # press on a regular key
                with self._sticky_lock:
                    if self._sticky_phys_down:
                        self._sticky_typed_while_mod.update(self._sticky_phys_down)
                    if self._sticky_latched:
                        self._sticky_release_on_next = True
            elif value == 0:  # release
                with self._sticky_lock:
                    release_on_next = self._sticky_release_on_next
                    self._sticky_release_on_next = False
                if release_on_next:
                    self._release_sticky_latches()
            return

        if not self.key_sender:
            return

        latching = self.sticky_enabled and not self.overlay_active

        if value == 1:  # press
            with self._sticky_lock:
                self._sticky_typed_while_mod.discard(code)
                self._sticky_phys_down.add(code)
                must_release = latching and bool(self._sticky_latched)
            if must_release:
                self._release_sticky_latches()
        elif value == 0:  # release
            with self._sticky_lock:
                was_down = code in self._sticky_phys_down
                self._sticky_phys_down.discard(code)
                typed_while_mod = code in self._sticky_typed_while_mod
                if typed_while_mod:
                    self._sticky_typed_while_mod.discard(code)
                should_latch = latching and was_down and not typed_while_mod
                if should_latch:
                    self._sticky_latched.add(code)
            if should_latch:
                self.key_sender.xtest_modifier_press(code)

        self._emit_modifiers()

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

                if self._sticky_release_pending:
                    self._sticky_release_pending = False
                    try:
                        self._release_sticky_latches()
                    except Exception:
                        pass
                if self._sticky_reset_pending:
                    self._sticky_reset_pending = False
                    with self._sticky_lock:
                        self._sticky_phys_down.clear()
                        self._sticky_typed_while_mod.clear()
                        self._sticky_release_on_next = False
                    self._emit_modifiers()

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
                            if event.value in (0, 1):
                                self._handle_sticky_event(event.code, event.value)
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
            self._release_sticky_latches()
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
        icon_path = Path(__file__).parent / "icons" / "tray-icon.png"
        if not icon_path.exists():
            icon_path = Path(__file__).parent / "app_icon.png"
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
        self.sticky_enabled = False
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                self.selected_items = [KeySymbol.from_dict(d) for d in data.get("items", [])]
                self.sticky_enabled = bool(data.get("sticky_keys", False))
            except:
                self.selected_items = []
        else:
            self.selected_items = []

    def save_config(self):
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True)
        data = {
            "items": [item.to_dict() for item in self.selected_items],
            "sticky_keys": bool(getattr(self, "sticky_enabled", False)),
        }
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def update_available_list(self):
        self.available_list.clear()
        all_avail = get_all_available()
        for item in all_avail:
            already = any(s.name == item.name for s in self.selected_items)
            if not already:
                list_item = QListWidgetItem(f"{item.display} ({item.name})")
                list_item.setData(Qt.UserRole, item.name)
                self.available_list.addItem(list_item)

    def update_selected_list(self):
        self.selected_list.clear()
        for item in self.selected_items:
            list_item = QListWidgetItem(f"{item.display} ({item.name})")
            list_item.setData(Qt.UserRole, item.name)
            self.selected_list.addItem(list_item)

    def add_item(self):
        current = self.available_list.currentItem()
        if current:
            name = current.data(Qt.UserRole)
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
            name = current.data(Qt.UserRole)
            self.selected_items = [s for s in self.selected_items if s.name != name]
            self.update_available_list()
            self.update_selected_list()

    def on_ok(self):
        self.save_config()
        self.hide()
        self.start_hotkey_listener()

    def set_sticky_enabled(self, enabled):
        self.sticky_enabled = bool(enabled)
        if self.hotkey_listener:
            self.hotkey_listener.set_sticky_enabled(self.sticky_enabled)
        self.save_config()
        print(f"DEBUG: Teclas de aderência {'ATIVADAS' if self.sticky_enabled else 'desativadas'}", flush=True)

    def release_stuck_modifiers(self):
        """Release modifier keys that the system still reports as pressed"""
        if self.hotkey_listener:
            return self.hotkey_listener.release_pressed_modifiers()
        return []

    def detected_modifiers(self):
        if self.hotkey_listener:
            return self.hotkey_listener.pressed_modifiers()
        return []

    def start_hotkey_listener(self):
        if self.hotkey_listener is None:
            self.hotkey_listener = GlobalHotkeyListener()
            self.hotkey_listener.key_sender = self.key_sender
            self.hotkey_listener.set_sticky_enabled(self.sticky_enabled)
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
            self.hotkey_listener.modifiers_changed.connect(
                self.selection_window.on_modifiers_changed, type=Qt.QueuedConnection)
            self.hotkey_listener.set_overlay_active(True)
        self.selection_window.show()

    def on_selection_closed(self):
        if self.hotkey_listener:
            try:
                self.hotkey_listener.key_pressed.disconnect()
            except TypeError:
                pass
            try:
                self.hotkey_listener.modifiers_changed.disconnect()
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
        self._suppress_auto_check_until = 0.0

        # Set window flags BEFORE any other operations
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_X11NetWmWindowTypeUtility)
        self.setFocusPolicy(Qt.NoFocus)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Selecione")
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.setStyleSheet("""
            QListWidget {
                background-color: #2d3a4f;
                color: #ffffff;
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
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3d4a5c;
                border-radius: 3px;
                background-color: #2d3a4f;
            }
            QCheckBox::indicator:checked {
                background-color: #FFD700;
                border-color: #FFD700;
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
        self.frame = frame
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Selecione uma opção")
        title.setStyleSheet("font-weight: bold; color: #ffffff;")
        frame_layout.addWidget(title)

        self.list_widget = QListWidget()
        for item in self.items:
            self.list_widget.addItem(f"{item.display} ({item.name})")
        self.list_widget.setCurrentRow(0)
        self.list_widget.itemClicked.connect(self.on_item_click)
        frame_layout.addWidget(self.list_widget)

        self.sticky_cb = QCheckBox("Teclas de aderência")
        self.sticky_cb.setToolTip(
            "Marque para ativar as teclas de aderência do Amarelo Keys.\n"
            "Desmarque para liberar as teclas modificadoras que o sistema ainda\n"
            "considera pressionadas (Shift, Ctrl, Alt)."
        )
        self.sticky_cb.toggled.connect(self.on_sticky_toggled)
        frame_layout.addWidget(self.sticky_cb)

        self.sticky_status = QLabel("")
        self.sticky_status.setWordWrap(True)
        frame_layout.addWidget(self.sticky_status)

        self._sticky_poll = QTimer(self)
        self._sticky_poll.setInterval(250)
        self._sticky_poll.timeout.connect(self.refresh_sticky_state)

        self.refresh_sticky_state()

        hint = QLabel("↑↓ Navegar  |  Enter: Enviar  |  Esc: Sair")
        hint.setStyleSheet("color: #ffffff; font-size: 10px;")
        frame_layout.addWidget(hint)

        layout.addWidget(frame, 0, Qt.AlignCenter)

    def on_sticky_toggled(self, checked):
        """Checkbox liga/desliga a aderência e libera as teclas modificadoras presas"""
        if self.parent_window is None:
            return
        import time
        self._user_action_time = time.time()
        self._user_checked = checked
        if checked:
            self.parent_window.set_sticky_enabled(True)
            system_sticky_enable()
            system_toggle_enable()
            self.refresh_sticky_state()
            return

        released = self.parent_window.release_stuck_modifiers()
        self.parent_window.set_sticky_enabled(False)
        system_sticky_disable()
        system_toggle_disable()
        if released:
            names = ", ".join(MODIFIER_NAMES.get(c, f"tecla {c}") for c in released)
            note = f"Tecla liberada: {names}"
        else:
            note = "Nenhuma tecla modificadora estava pressionada"
        self.refresh_sticky_state(note)

    def on_modifiers_changed(self, codes):
        self.refresh_sticky_state()

    def _detected_modifiers(self):
        codes = set()
        if self.parent_window is not None:
            codes.update(self.parent_window.detected_modifiers())
        return sorted(codes)

    def refresh_sticky_state(self, note=None):
        """Evaluate sticky/toggle keys state of the system and pressed modifiers"""
        if not hasattr(self, "sticky_cb"):
            return
        sticky_sys, toggle_sys = system_sticky_state()
        app_sticky = bool(getattr(self.parent_window, "sticky_enabled", False))
        codes = self._detected_modifiers()

        self.sticky_cb.blockSignals(True)
        import time
        # If user just acted recently, respect their action
        user_action_time = getattr(self, '_user_action_time', 0)
        if time.time() - user_action_time < 1.5:
            should_check = getattr(self, '_user_checked', (sticky_sys or toggle_sys or app_sticky or bool(codes)))
        else:
            should_check = sticky_sys or toggle_sys or app_sticky or bool(codes)
        self.sticky_cb.setChecked(should_check)
        self.sticky_cb.blockSignals(False)

        state = (
            f"Sistema: aderência {'ATIVA' if sticky_sys else 'inativa'}"
            f" · alternância {'ATIVA' if toggle_sys else 'inativa'}"
            f" · app {'ATIVO' if app_sticky else 'inativo'}"
        )

        if codes:
            names = ", ".join(MODIFIER_NAMES.get(c, f"tecla {c}") for c in codes)
            self.sticky_status.setStyleSheet("color: #FFD700; font-size: 11px;")
            self.sticky_cb.setStyleSheet("QCheckBox { color: #FFD700; }")
            state = f"{names} pressionada(s) - desmarque para liberar\n{state}"
        else:
            self.sticky_status.setStyleSheet("color: #aaaaaa; font-size: 11px;")
            self.sticky_cb.setStyleSheet("")

        if note:
            state = f"{note}\n{state}"
        self.sticky_status.setText(state)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if not self.frame.geometry().contains(event.pos()):
            self.hide()
            self.closed.emit()
        super().mousePressEvent(event)

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
        self.refresh_sticky_state()
        self._sticky_poll.start()

    def hide(self):
        self._sticky_poll.stop()
        super().hide()


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