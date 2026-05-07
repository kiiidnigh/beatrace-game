import os
import sys
import json
import hashlib
import subprocess
import shutil
from config.settings import APPDATA_DIR

# Pfade
SETTINGS_FILE = os.path.join(APPDATA_DIR, "settings.json")
OBS_BASE_DIR = os.path.join(APPDATA_DIR, "output", "obs")
FL_USER_TEMPLATES_DIR = os.path.expanduser(r"~\Documents\Image-Line\FL Studio\Projects\Templates")


def _create_fl_studio_shortcut(shortcut_path):
    """Erstellt eine Windows-Verknüpfung (.lnk) zum FL Studio Dokumente-Ordner."""
    os.makedirs(FL_USER_TEMPLATES_DIR, exist_ok=True)

    vbs_script = f"""
    Set ws = CreateObject("WScript.Shell")
    Set shortcut = ws.CreateShortcut("{shortcut_path}")
    shortcut.TargetPath = "{FL_USER_TEMPLATES_DIR}"
    shortcut.Description = "Hier speichert FL Studio eigene Templates"
    shortcut.Save
    """

    vbs_path = os.path.join(os.path.dirname(shortcut_path), "create_shortcut.vbs")
    try:
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_script)
        subprocess.run(["cscript", "//Nologo", vbs_path], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"Verknüpfung konnte nicht erstellt werden: {e}")
    finally:
        if os.path.exists(vbs_path):
            os.remove(vbs_path)


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
    """Speichert Einstellungen formatiert im AppData-Verzeichnis."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Fehler beim Speichern der Settings: {e}")


def get_obs_path(player_name):
    """Gibt den Pfad zur OBS-Textdatei im AppData-Verzeichnis zurück."""
    os.makedirs(OBS_BASE_DIR, exist_ok=True)
    return os.path.join(OBS_BASE_DIR, f"obs_timer_{player_name}.txt")


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


def open_template_folder():
    """Öffnet den internen Template-Ordner im Windows Explorer."""
    template_dir = os.path.join(APPDATA_DIR, "templates", "flstudio")
    os.makedirs(template_dir, exist_ok=True)
    os.startfile(template_dir)


def get_available_templates():
    """Scannt sowohl den AppData-Ordner als auch den FL Studio User-Ordner."""
    template_map = {}

    # 1. Interne App-Templates
    appdata_dir = os.path.join(APPDATA_DIR, "templates", "flstudio")
    if not os.path.exists(appdata_dir):
        # Initialisiert Ordner und default.flp, falls noch nicht geschehen
        get_template_path("")

    if os.path.exists(appdata_dir):
        for f in os.listdir(appdata_dir):
            if f.endswith(".flp"):
                template_map[f"{f} (App)"] = os.path.join(appdata_dir, f)

    # 2. FL Studio User-Templates
    if os.path.exists(FL_USER_TEMPLATES_DIR):
        for root, dirs, files in os.walk(FL_USER_TEMPLATES_DIR):
            for f in files:
                if f.endswith(".flp"):
                    rel_path = os.path.relpath(os.path.join(root, f), FL_USER_TEMPLATES_DIR)
                    template_map[f"{rel_path} (FL Studio)"] = os.path.join(root, f)

    return template_map


def get_template_path(selected_path):
    """Prüft, ob der gewählte Pfad existiert, sonst Fallback auf interne default.flp."""
    template_dir = os.path.join(APPDATA_DIR, "templates", "flstudio")
    appdata_template_path = os.path.join(template_dir, "default.flp")

    # Ordner und Shortcut sicherstellen
    os.makedirs(template_dir, exist_ok=True)
    shortcut_path = os.path.join(template_dir, "FL Templates.lnk")
    if not os.path.exists(shortcut_path):
        _create_fl_studio_shortcut(shortcut_path)

    # Wenn die default.flp noch nicht im AppData liegt, kopieren wir sie aus den Assets
    if not os.path.exists(appdata_template_path):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(__file__))

        original_asset_path = os.path.join(base_dir, "assets", "default.flp")
        if os.path.exists(original_asset_path):
            shutil.copy2(original_asset_path, appdata_template_path)

    # Wenn der übergebene Pfad existiert (z.B. User Template), nimm den
    if selected_path and os.path.exists(selected_path):
        return selected_path

    # Sonst nimm die default.flp als absoluten Fallback
    return appdata_template_path if os.path.exists(appdata_template_path) else ""