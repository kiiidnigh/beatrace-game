# ================================================
# FILE: services/workspace_service.py
# ================================================
import logging
import os
import re
from utils.file_utils import load_workspaces, save_workspaces, read_workspace_id
from services.base_service import BaseService

class WorkspaceService(BaseService):
    def __init__(self):
        super().__init__()
        self._data = load_workspaces()
        if "known_folders" not in self._data:
            self._data["known_folders"] = []
        self.register_listeners()

    def _save(self):
        save_workspaces(self._data)

    def cycle_match_folder(self, base_folder):
        if not base_folder or not os.path.exists(base_folder):
            return ""
        workspace_file = os.path.join(base_folder, ".beatrace_workspace")
        if os.path.exists(workspace_file):
            try:
                os.remove(workspace_file)
            except Exception as e:
                logging.warning(f"[WorkspaceService] Konnte alte Signatur nicht löschen: {e}")

        max_num = 0
        try:
            for d in os.listdir(base_folder):
                if os.path.isdir(os.path.join(base_folder, d)):
                    match = re.match(r"Beatrace_Match_(\d+)", d)
                    if match:
                        max_num = max(max_num, int(match.group(1)))
        except Exception as e:
            logging.error(f"[WorkspaceService] Fehler beim Suchen der Match-Ordner: {e}")

        new_folder_name = f"Beatrace_Match_{max_num + 1}"
        os.makedirs(os.path.join(base_folder, new_folder_name), exist_ok=True)
        return new_folder_name

    def add_known_folder(self, base_folder_path):
        if not base_folder_path or not os.path.exists(base_folder_path):
            return False
        norm_path = os.path.normpath(base_folder_path)
        if norm_path not in self._data["known_folders"]:
            self._data["known_folders"].append(norm_path)
            self._save()
            logging.info(f"[WorkspaceService] Neuer lokaler Ordner registriert: {norm_path}")
        return True

    def get_auto_join_path(self, workspace_id):
        if not workspace_id:
            return None
        for folder in self._data["known_folders"]:
            if os.path.isdir(folder):
                current_id = read_workspace_id(folder)
                if current_id == workspace_id:
                    logging.info(f"[WorkspaceService] Live-Handshake erfolgreich für Auto-Join: {folder}")
                    return folder
        return None