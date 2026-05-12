# ================================================
# FILE: services/workspace_service.py
# ================================================
import logging
import os
from utils.file_utils import load_workspaces, save_workspaces


class WorkspaceService:
    @staticmethod
    def add_workspace(workspace_id, base_folder_path):
        """Speichert einen neuen oder aktualisiert einen bestehenden Workspace."""
        if not workspace_id or not base_folder_path:
            return False

        data = load_workspaces()
        if "workspaces" not in data:
            data["workspaces"] = {}

        # Wenn der Ordner schon unter dieser ID gespeichert ist, machen wir nichts
        if data["workspaces"].get(workspace_id) == base_folder_path:
            return True

        data["workspaces"][workspace_id] = base_folder_path
        save_workspaces(data)
        logging.info(f"[WorkspaceService] Workspace '{workspace_id}' lokal registriert: {base_folder_path}")
        return True

    @staticmethod
    def get_path_by_id(workspace_id):
        """Sucht nach dem lokalen Pfad anhand der Workspace-Signatur."""
        if not workspace_id:
            return None

        data = load_workspaces()
        return data.get("workspaces", {}).get(workspace_id)

    @staticmethod
    def get_all_workspaces():
        """Gibt ein Dictionary aller bekannten Workspaces zurück {id: path}."""
        data = load_workspaces()
        return data.get("workspaces", {})

    @staticmethod
    def get_auto_join_path(workspace_id):
        """
        Business Logic: Prüft, ob ein Workspace bekannt ist UND der Ordner real existiert.
        Gibt den lokalen Pfad zurück, wenn ein Auto-Join sicher möglich ist, ansonsten None.
        """
        if not workspace_id:
            return None

        path = WorkspaceService.get_path_by_id(workspace_id)

        # SoC: Der Service kümmert sich um die Dateisystem-Validierung, nicht das UI!
        if path and os.path.isdir(path):
            return path

        return None