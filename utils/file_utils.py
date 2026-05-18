# ================================================
# FILE: utils/file_utils.py
# ================================================
import os
import sys
import json
import hashlib
import subprocess
import shutil
import logging
from config import settings

# Pfade
OBS_BASE_DIR = os.path.join(settings.APPDATA_DIR, "output", "obs")
FL_USER_TEMPLATES_DIR = os.path.expanduser(r"~\Documents\Image-Line\FL Studio\Projects\Templates")


def _get_profile_suffix():
    """Hilfsfunktion: Holt das Dev-Profil (z.B. '_tester'), falls vorhanden."""
    profile = os.environ.get("BEATRACE_PROFILE", "")
    return f"_{profile}" if profile else ""

# --- SICHERERE JSON HELPER ---
def _safe_json_load(path, default_factory=dict):
    if not os.path.exists(path):
        return default_factory()

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        backup_path = path + ".corrupt.bak"
        shutil.copy2(path, backup_path)
        logging.error(f"[FileUtils] JSON-FEHLER! Datei {path} ist korrupt. Backup: {backup_path} | Fehler: {e}")

        from core.event_bus import EventBus
        from core.events import SysEvents
        EventBus.emit(SysEvents.FILE_CORRUPTED, {"file": os.path.basename(path)})

        return default_factory()
    except Exception as e:
        logging.error(f"[FileUtils] Unerwarteter Lesefehler bei {path}: {e}")
        return default_factory()

def _safe_json_save(path, data_dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=4)
    except Exception as e:
        logging.error(f"[FileUtils] Fehler beim Speichern von {path}: {e}")

# --- SETTINGS & STATE ---
def get_prefs_path(): return os.path.join(settings.APPDATA_DIR, f"settings{_get_profile_suffix()}.json")
def load_prefs(): return _safe_json_load(get_prefs_path())
def save_prefs(prefs_dict): _safe_json_save(get_prefs_path(), prefs_dict)

def get_social_path(): return os.path.join(settings.APPDATA_DIR, f"social{_get_profile_suffix()}.json")
def load_social(): return _safe_json_load(get_social_path())
def save_social(social_dict): _safe_json_save(get_social_path(), social_dict)

def get_workspaces_path(): return os.path.join(settings.APPDATA_DIR, f"workspaces{_get_profile_suffix()}.json")
def load_workspaces(): return _safe_json_load(get_workspaces_path())
def save_workspaces(workspaces_dict): _safe_json_save(get_workspaces_path(), workspaces_dict)

def get_profile_path(): return os.path.join(settings.APPDATA_DIR, f"user_profile{_get_profile_suffix()}.json")
def load_profile(): return _safe_json_load(get_profile_path())
def save_profile(profile_dict): _safe_json_save(get_profile_path(), profile_dict)

# --- FL STUDIO SHORTCUTS & TEMPLATES ---
def _create_fl_studio_shortcut(shortcut_path):
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
        logging.error(f"Verknüpfung konnte nicht erstellt werden: {e}")
    finally:
        if os.path.exists(vbs_path):
            os.remove(vbs_path)

def get_obs_path(player_name):
    os.makedirs(OBS_BASE_DIR, exist_ok=True)
    return os.path.join(OBS_BASE_DIR, f"obs_timer_{player_name}.txt")

def calculate_md5(fname):
    hash_md5 = hashlib.md5()
    if not os.path.exists(fname): return None
    try:
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None

def open_template_folder():
    template_dir = os.path.join(settings.APPDATA_DIR, "templates", "flstudio")
    os.makedirs(template_dir, exist_ok=True)
    os.startfile(template_dir)

def get_available_templates():
    template_map = {}
    appdata_dir = os.path.join(settings.APPDATA_DIR, "templates", "flstudio")
    if not os.path.exists(appdata_dir):
        get_template_path("")

    if os.path.exists(appdata_dir):
        for f in os.listdir(appdata_dir):
            if f.endswith(".flp"):
                template_map[f"{f} (App)"] = os.path.join(appdata_dir, f)

    if os.path.exists(FL_USER_TEMPLATES_DIR):
        for root, dirs, files in os.walk(FL_USER_TEMPLATES_DIR):
            for f in files:
                if f.endswith(".flp"):
                    rel_path = os.path.relpath(os.path.join(root, f), FL_USER_TEMPLATES_DIR)
                    template_map[f"{rel_path} (FL Studio)"] = os.path.join(root, f)
    return template_map

def get_template_path(selected_path):
    template_dir = os.path.join(settings.APPDATA_DIR, "templates", "flstudio")
    appdata_template_path = os.path.join(template_dir, "default.flp")

    os.makedirs(template_dir, exist_ok=True)
    shortcut_path = os.path.join(template_dir, "FL Templates.lnk")
    if not os.path.exists(shortcut_path):
        _create_fl_studio_shortcut(shortcut_path)

    if not os.path.exists(appdata_template_path):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(__file__))

        original_asset_path = os.path.join(base_dir, "assets", "default.flp")
        if os.path.exists(original_asset_path):
            shutil.copy2(original_asset_path, appdata_template_path)

    if selected_path and os.path.exists(selected_path):
        return selected_path

    return appdata_template_path if os.path.exists(appdata_template_path) else ""