# ================================================
# FILE: services/workspace_service.py
# ================================================
import logging
import os
import re
from utils.file_utils import load_workspaces, save_workspaces, read_workspace_id


class WorkspaceService:

    @staticmethod
    def cycle_match_folder(base_folder):
        """
        Business Logic: Sucht den höchsten Match-Ordner, erstellt den nächsten
        und löscht den alten Workspace-Token, um einen sauberen State zu erzwingen.
        Gibt den neuen Ordnernamen zurück.
        """
        if not base_folder or not os.path.exists(base_folder):
            return ""

        # 1. Alte Signatur zwingend löschen
        workspace_file = os.path.join(base_folder, ".beatrace_workspace")
        if os.path.exists(workspace_file):
            try:
                os.remove(workspace_file)
            except Exception as e:
                logging.warning(f"[WorkspaceService] Konnte alte Signatur nicht löschen: {e}")

        # 2. Höchsten Ordner finden
        max_num = 0
        try:
            for d in os.listdir(base_folder):
                if os.path.isdir(os.path.join(base_folder, d)):
                    match = re.match(r"Beatrace_Match_(\d+)", d)
                    if match:
                        max_num = max(max_num, int(match.group(1)))
        except Exception as e:
            logging.error(f"[WorkspaceService] Fehler beim Suchen der Match-Ordner: {e}")

        # 3. Neuen Ordner anlegen
        new_folder_name = f"Beatrace_Match_{max_num + 1}"
        os.makedirs(os.path.join(base_folder, new_folder_name), exist_ok=True)

        return new_folder_name

    @staticmethod
    def add_known_folder(base_folder_path):
        """Speichert nur noch den Pfad in der Historie (Live-Handshake Prinzip)."""
        if not base_folder_path or not os.path.exists(base_folder_path):
            return False

        data = load_workspaces()
        if "known_folders" not in data:
            data["known_folders"] = []

        norm_path = os.path.normpath(base_folder_path)

        if norm_path not in data["known_folders"]:
            data["known_folders"].append(norm_path)
            save_workspaces(data)
            logging.info(f"[WorkspaceService] Neuer lokaler Ordner registriert: {norm_path}")

        return True

    @staticmethod
    def get_auto_join_path(workspace_id):
        """
        Business Logic (LIVE-CHECK):
        Prüft bei bekannten Ordnern in Echtzeit, ob die übergebene Workspace-ID existiert.
        Gibt den lokalen Pfad zurück, wenn ein Auto-Join sicher möglich ist, ansonsten None.
        """
        if not workspace_id:
            return None

        data = load_workspaces()
        known_folders = data.get("known_folders", [])

        for folder in known_folders:
            if os.path.isdir(folder):
                # Live Handshake: Wir lesen die Datei auf der Festplatte JETZT aus
                current_id = read_workspace_id(folder)
                if current_id == workspace_id:
                    logging.info(f"[WorkspaceService] Live-Handshake erfolgreich für Auto-Join: {folder}")
                    return folder

        return None