"""Settings persistence. Pure import never reads or writes user configuration.

The application calls initialize_paths with GLib's directories before UI creation.
Tests may supply isolated directories, without importing GI.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from .data import DEFAULT_SETTINGS
from .resource_loader import read_resource

CALCPAD_LANG = read_resource("calcpad.lang")
CFG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "calcpad-gui"
CFG_FILE = CFG_DIR / "settings.json"
LANG_DIR = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "gtksourceview-5" / "language-specs"
LANG_FILE = LANG_DIR / "calcpad.lang"


def initialize_paths(config_dir: str, data_dir: str) -> None:
    """Retain historical GLib paths and startup mkdir/error semantics."""
    global CFG_DIR, CFG_FILE, LANG_DIR, LANG_FILE
    CFG_DIR = Path(config_dir) / "calcpad-gui"
    CFG_FILE = CFG_DIR / "settings.json"
    LANG_DIR = Path(data_dir) / "gtksourceview-5" / "language-specs"
    LANG_FILE = LANG_DIR / "calcpad.lang"
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    LANG_DIR.mkdir(parents=True, exist_ok=True)

def load_settings():
    data = dict(DEFAULT_SETTINGS)
    if CFG_FILE.exists():
        try:
            loaded = json.loads(CFG_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update({k:v for k,v in loaded.items() if k in DEFAULT_SETTINGS})
        except (OSError, json.JSONDecodeError):
            pass
    return data

def save_settings(s):
    try: CFG_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")
    except OSError: pass
