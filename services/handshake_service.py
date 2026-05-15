# ================================================
# FILE: services/handshake_service.py
# ================================================
import os
import time
import threading
import logging
from core.event_bus import EventBus
from utils.file_utils import get_or_create_workspace_id
from services.base_service import BaseService

class HandshakeService(BaseService):
    def __init__(self, workspace_service):
        super().__init__()
        self.workspace_service = workspace_service
        self._is_checking = False

        self._listeners = {
            "CMD_PREPARE_WORKSPACE": self._prepare_workspace,
            "CMD_VERIFY_WORKSPACE": self._verify_workspace,
            "CMD_STOP_HANDSHAKE_CHECK": self._stop_check_loop
        }
        self.register_listeners()

        logging.info("[HandshakeService] Bereit für schnelle Workspace-Verifikation.")

    def cleanup(self):
        self._is_checking = False
        super().cleanup()

    def _prepare_workspace(self, data):
        base_folder = data.get("base_folder")
        if not base_folder:
            EventBus.emit("SYS_HANDSHAKE_ERROR", data={"error": "Kein Ordner übergeben"})
            return

        def task():
            try:
                wid = get_or_create_workspace_id(base_folder)
                if not wid:
                    EventBus.emit("SYS_HANDSHAKE_ERROR", data={"error": "Konnte Workspace ID nicht erstellen/lesen."})
                    return

                # FIX: Wir nutzen den injizierten Service
                self.workspace_service.add_known_folder(base_folder)
                logging.info(f"[HandshakeService] Workspace ID generiert/geladen: {wid}")
                EventBus.emit("SYS_WORKSPACE_READY", data={"workspace_id": wid})
            except Exception as e:
                logging.error(f"[HandshakeService] Fehler bei Workspace-Init: {e}")
                EventBus.emit("SYS_HANDSHAKE_ERROR", data={"error": str(e)})

        threading.Thread(target=task, daemon=True).start()

    def _verify_workspace(self, data):
        if self._is_checking:
            return

        self._is_checking = True
        base_folder = data.get("base_folder")
        expected_id = data.get("workspace_id")

        if not base_folder or not expected_id:
            EventBus.emit("SYS_HANDSHAKE_TIMEOUT")
            self._is_checking = False
            return

        def check_loop():
            logging.info(f"[HandshakeService] Prüfe lokale Signatur für ID: {expected_id}...")
            attempts = 0
            max_attempts = 5
            workspace_file = os.path.join(base_folder, ".beatrace_workspace")

            while self._is_checking and attempts < max_attempts:
                if os.path.exists(workspace_file):
                    try:
                        with open(workspace_file, "r", encoding="utf-8") as f:
                            local_id = f.read().strip()
                            if local_id == expected_id:
                                logging.info("[HandshakeService] Ordner blitzschnell verifiziert!")
                                # FIX: Wir nutzen den injizierten Service
                                self.workspace_service.add_known_folder(base_folder)
                                EventBus.emit("SYS_HANDSHAKE_SUCCESS")
                                self._is_checking = False
                                return
                            else:
                                logging.warning("[HandshakeService] Signatur existiert, passt aber nicht zur Lobby!")
                                EventBus.emit("SYS_HANDSHAKE_TIMEOUT")
                                self._is_checking = False
                                return
                    except Exception as e:
                        logging.debug(f"[HandshakeService] Lesefehler Signatur: {e}")

                time.sleep(2)
                attempts += 1

            if self._is_checking:
                logging.warning("[HandshakeService] Falscher Ordner oder Cloud extrem langsam. Timeout!")
                EventBus.emit("SYS_HANDSHAKE_TIMEOUT")
                self._is_checking = False

        threading.Thread(target=check_loop, daemon=True).start()

    def _stop_check_loop(self, data=None):
        self._is_checking = False