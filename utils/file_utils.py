import os
import sys
import json
import hashlib
from config.settings import APPDATA_DIR

# Pfade zeigen jetzt in das AppData-Verzeichnis
SETTINGS_FILE = os.path.join(APPDATA_DIR, "settings.json")
OBS_BASE_DIR = os.path.join(APPDATA_DIR, "output", "obs")

def load_prefs():
    """Lädt die Einstellungen aus dem AppData-Verzeichnis."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_prefs(prefs):
    """Speichert Einstellungen formatiert (indent=4) im AppData-Verzeichnis."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            # indent=4 sorgt für die gewünschte übersichtliche Struktur
            json.dump(prefs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Fehler beim Speichern der Settings: {e}")

def get_obs_path(player_name):
    """Gibt den Pfad zur OBS-Textdatei im AppData-Verzeichnis zurück."""
    os.makedirs(OBS_BASE_DIR, exist_ok=True)
    return os.path.join(OBS_BASE_DIR, f"obs_timer_{player_name}.txt")

def get_template_path():
    """Templates sind statisch und bleiben im Installationsordner (Assets)."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "template.flp")

def calculate_md5(fname):
    """Berechnet den MD5 Hash einer Datei."""
    hash_md5 = hashlib.md5()
    if not os.path.exists(fname):
        return None
    try:
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None


def get_template_path():
    """Findet das Template, egal ob in PyCharm oder als fertige .exe"""
    if getattr(sys, 'frozen', False):
        # Wenn das Programm als .exe läuft, liegt der assets-Ordner direkt neben der .exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Im Entwicklungsmodus (PyCharm) gehen wir einen Ordner hoch
        base_dir = os.path.dirname(os.path.dirname(__file__))

    return os.path.join(base_dir, "assets", "template.flp")