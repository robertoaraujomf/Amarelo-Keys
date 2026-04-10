import json
import os
import threading
from dataclasses import dataclass, asdict, field
from typing import Optional
from pathlib import Path


@dataclass
class KeyMapping:
    trigger_key: str
    target_key: str
    disable_original: bool = False
    enabled: bool = True


@dataclass
class KeyMappings:
    mappings: list[KeyMapping] = field(default_factory=list)


class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "amarelo-keys"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "mappings.json"
        self._lock = threading.Lock()
        self._mappings: dict[str, KeyMapping] = {}
        self._disabled_keys: set[str] = set()
        self._load()
    
    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                for m in data.get("mappings", []):
                    mapping = KeyMapping(**m)
                    self._mappings[mapping.trigger_key] = mapping
                    if mapping.disable_original:
                        self._disabled_keys.add(mapping.trigger_key)
            except (json.JSONDecodeError, TypeError):
                pass
    
    def _save(self):
        with self._lock:
            data = {"mappings": [asdict(m) for m in self._mappings.values()]}
            with open(self.config_file, "w") as f:
                json.dump(data, f, indent=2)
    
    def add_mapping(self, trigger_key: str, target_key: str, disable_original: bool = False) -> KeyMapping:
        mapping = KeyMapping(
            trigger_key=trigger_key,
            target_key=target_key,
            disable_original=disable_original
        )
        self._mappings[trigger_key] = mapping
        if disable_original:
            self._disabled_keys.add(trigger_key)
        else:
            self._disabled_keys.discard(trigger_key)
        self._save()
        return mapping
    
    def remove_mapping(self, trigger_key: str):
        if trigger_key in self._mappings:
            del self._mappings[trigger_key]
            self._disabled_keys.discard(trigger_key)
            self._save()
    
    def get_mapping(self, trigger_key: str) -> Optional[KeyMapping]:
        return self._mappings.get(trigger_key)
    
    def get_all_mappings(self) -> list[KeyMapping]:
        return list(self._mappings.values())
    
    def is_key_disabled(self, key: str) -> bool:
        return key in self._disabled_keys
    
    def update_mapping(self, trigger_key: str, enabled: bool = None, 
                       disable_original: bool = None):
        if trigger_key in self._mappings:
            mapping = self._mappings[trigger_key]
            if enabled is not None:
                mapping.enabled = enabled
            if disable_original is not None:
                mapping.disable_original = disable_original
                if disable_original:
                    self._disabled_keys.add(trigger_key)
                else:
                    self._disabled_keys.discard(trigger_key)
            self._save()
