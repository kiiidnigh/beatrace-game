# ================================================
# FILE: services/workspace_service.py
# ================================================
import logging
import os
import shutil
from config import settings
from services.base_service import BaseService


class WorkspaceService(BaseService):
    def __init__(self):
        super().__init__()
        # SRP & KISS: Wir verwalten keine lokalen Drive-Ordner mehr.
        # Alles passiert in diesem versteckten Sandbox-Ordner.
        self.workspaces_dir = os.path.join(settings.APPDATA_DIR, "Workspaces")
        os.makedirs(self.workspaces_dir, exist_ok=True)
        self.register_listeners()

    def setup_match_workspace(self, game_state):
        """
        Überschreibt die Pfade im GameState mit dem lokalen Sandbox-Ordner.
        DRY: Wird von Host und Client beim Starten des Matches aufgerufen.
        """
        game_state.local_drive_folder = self.workspaces_dir
        game_state.match_folder_name = f"Match_{game_state.room_code}"

        # Stelle sicher, dass der Ordner physisch existiert
        os.makedirs(game_state.local_match_dir, exist_ok=True)
        logging.info(f"[WorkspaceService] Sandbox bereit: {game_state.local_match_dir}")

    def cleanup_match_workspace(self, room_code):
        """Fail Fast / Cleanup: Löscht den Sandbox-Ordner nach dem Match, um Müll zu vermeiden."""
        path = os.path.join(self.workspaces_dir, f"Match_{room_code}")
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                logging.info(f"[WorkspaceService] Sandbox gelöscht: {path}")
            except Exception as e:
                logging.error(f"[WorkspaceService] Sandbox konnte nicht gelöscht werden: {e}")