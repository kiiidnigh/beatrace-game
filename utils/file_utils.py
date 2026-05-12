# ================================================
# FILE: utils/file_utils.py
# ================================================
import os
import sys
import json
import hashlib
import subprocess
import shutil
import uuid
from config import settings

# Pfade
OBS_BASE_DIR = os.path.join(settings.APPDATA_DIR, "output", "obs")
FL_USER_TEMPLATES_DIR = os.path.expanduser(r"~\Documents\Image-Line\FL Studio\Projects\Templates")


def _get_profile_suffix():
    """Hilfsfunktion: Holt das Dev-Profil (z.B. '_tester'), falls vorhanden."""
    profile = os.environ.get("BEATRACE_PROFILE", "")
    return f"_{profile}" if profile else ""

# --- SETTINGS (App-Konfiguration) ---
def get_prefs_path():
    # Speichert z.B. unter %AppData%\Beatrace\settings_tester.json
    return os.path.join(settings.APPDATA_DIR, f"settings{_get_profile_suffix()}.json")

def load_prefs():
    path = get_prefs_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_prefs(prefs_dict):
    path = get_prefs_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(prefs_dict, f, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern der Settings: {e}")

# --- SOCIAL (Identität & Freunde) ---
def get_social_path():
    return os.path.join(settings.APPDATA_DIR, f"social{_get_profile_suffix()}.json")

def load_social():
    path = get_social_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_social(social_dict):
    path = get_social_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(social_dict, f, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern der Social-Daten: {e}")

# --- WORKSPACES (Cloud Basis-Ordner Historie) ---
def get_workspaces_path():
    return os.path.join(settings.APPDATA_DIR, f"workspaces{_get_profile_suffix()}.json")

def load_workspaces():
    path = get_workspaces_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_workspaces(workspaces_dict):
    path = get_workspaces_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(workspaces_dict, f, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern der Workspaces: {e}")


# --- FL STUDIO & MATCH LOGIK ---

def get_or_create_workspace_id(base_folder):
    """
    Liest oder erstellt die eindeutige Signatur des Cloud-Ordners.
    Das macht den Sync-Handshake instantan!
    """
    if not base_folder or not os.path.exists(base_folder):
        return ""

    workspace_file = os.path.join(base_folder, ".beatrace_workspace")

    # Wenn die Signatur schon existiert, einfach zurückgeben
    if os.path.exists(workspace_file):
        try:
            with open(workspace_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    # Ansonsten eine neue, eindeutige ID generieren
    new_id = str(uuid.uuid4())
    try:
        with open(workspace_file, "w", encoding="utf-8") as f:
            f.write(new_id)
    except Exception as e:
        import logging
        logging.error(f"[FileUtils] Konnte Workspace-ID nicht schreiben: {e}")

    return new_id


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
        print(f"Verknüpfung konnte nicht erstellt werden: {e}")
    finally:
        if os.path.exists(vbs_path):
            os.remove(vbs_path)


def get_obs_path(player_name):
    os.makedirs(OBS_BASE_DIR, exist_ok=True)
    return os.path.join(OBS_BASE_DIR, f"obs_timer_{player_name}.txt")


def calculate_md5(fname):
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

# --- USER PROFILE (Eigene Identität & Name) ---
def get_profile_path():
    return os.path.join(settings.APPDATA_DIR, f"user_profile{_get_profile_suffix()}.json")

def load_profile():
    path = get_profile_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_profile(profile_dict):
    path = get_profile_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile_dict, f, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern des Profils: {e}")