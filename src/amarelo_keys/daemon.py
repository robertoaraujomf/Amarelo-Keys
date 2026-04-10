import os
import sys
import time
import threading
from typing import Optional
from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController

from .config import ConfigManager


class KeyRemapperDaemon:
    def __init__(self):
        self.config = ConfigManager()
        self.keyboard_controller = KeyboardController()
        self._running = False
        self._held_trigger: Optional[str] = None
        self._pressed_keys: set = set()
        
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
    
    def start(self):
        self._running = True
        pid_file = "/tmp/amarelo-keys.pid"
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        
        print("Amarelo Keys daemon started")
        self._listener.start()
        
        while self._running:
            time.sleep(0.1)
    
    def stop(self):
        self._running = False
        self._listener.stop()
        pid_file = "/tmp/amarelo-keys.pid"
        if os.path.exists(pid_file):
            os.remove(pid_file)
        print("Amarelo Keys daemon stopped")
    
    def _on_press(self, key):
        try:
            key_name = self._get_key_name(key)
        except AttributeError:
            return
        
        if self._held_trigger:
            return
        
        mapping = self.config.get_mapping(key_name)
        if mapping and mapping.enabled:
            self._held_trigger = key_name
            return
        
        if self.config.is_key_disabled(key_name):
            return
        
        self._pressed_keys.add(key_name)
    
    def _on_release(self, key):
        try:
            key_name = self._get_key_name(key)
        except AttributeError:
            return
        
        if self._held_trigger == key_name:
            self._held_trigger = None
            return
        
        if self._held_trigger:
            trigger_mapping = self.config.get_mapping(self._held_trigger)
            if trigger_mapping and trigger_mapping.enabled:
                self._send_target_keys(trigger_mapping.target_key)
        
        self._pressed_keys.discard(key_name)
    
    def _send_target_keys(self, target: str):
        target_keys = target.split('+')
        
        for key_str in target_keys:
            key = self._parse_key(key_str.strip())
            if key:
                self.keyboard_controller.press(key)
        
        for key_str in reversed(target_keys):
            key = self._parse_key(key_str.strip())
            if key:
                self.keyboard_controller.release(key)
    
    def _parse_key(self, key_str: str) -> Optional[Key | KeyCode]:
        special_keys = {
            'ctrl': Key.ctrl,
            'control': Key.ctrl,
            'alt': Key.alt,
            'shift': Key.shift,
            'tab': Key.tab,
            'enter': Key.enter,
            'return': Key.enter,
            'space': Key.space,
            'backspace': Key.backspace,
            'delete': Key.delete,
            'esc': Key.esc,
            'escape': Key.esc,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'home': Key.home,
            'end': Key.end,
            'page_up': Key.page_up,
            'page_down': Key.page_down,
            'caps_lock': Key.caps_lock,
            'num_lock': Key.num_lock,
            'scroll_lock': Key.scroll_lock,
            'print_screen': Key.print_screen,
            'menu': Key.menu,
        }
        
        if key_str.lower() in special_keys:
            return special_keys[key_str.lower()]
        
        if len(key_str) == 1:
            return KeyCode.from_char(key_str.lower())
        
        return None
    
    def _get_key_name(self, key) -> str:
        if isinstance(key, Key):
            return key.name
        elif isinstance(key, KeyCode):
            if key.char:
                return key.char.lower()
            return str(key.vk)
        return str(key)
