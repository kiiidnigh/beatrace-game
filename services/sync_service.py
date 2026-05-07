import os
import time
import threading
import logging
from utils.file_utils import calculate_md5
from core.event_bus import EventBus


class SyncService:
    def __init__(self, project_path):
        self.project_path = project_path
        self._stop_event = threading.Event()
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        EventBus.subscribe("CMD_WAIT_FOR_LOCK", self._handle_wait_lock)
        EventBus.subscribe("CMD_WATCH_DOWNLOAD", self._handle_watch_download)
        EventBus.subscribe("CMD_STOP_SYNC_MONITOR", lambda d: self._stop_event.set())

    def _handle_wait_lock(self, data):
        max_attempts = data.get("max_attempts", 100)
        self._stop_event.clear()

        # Auslagerung in einen Hintergrund-Thread, um UI-Freezes zu verhindern
        def _wait():
            attempts = 0
            while attempts < max_attempts and not self._stop_event.is_set():
                if os.path.exists(self.project_path):
                    try:
                        # Teste, ob die Datei frei ist (umbenennen zu sich selbst)
                        os.rename(self.project_path, self.project_path)
                        file_hash = calculate_md5(self.project_path)
                        logging.info(f"[Sync] Dateifreigabe erkannt. Hash: {file_hash}")
                        EventBus.emit("SYNC_LOCK_RELEASED", data={"hash": file_hash})
                        return
                    except OSError:
                        pass  # Datei ist noch blockiert
                time.sleep(0.5)
                attempts += 1

            if not self._stop_event.is_set():
                logging.warning("[Sync] Timeout beim Warten auf Dateifreigabe.")
                EventBus.emit("SYNC_LOCK_TIMEOUT")

        threading.Thread(target=_wait, daemon=True).start()

    def _handle_watch_download(self, data):
        expected_hash = data.get("expected_hash")
        self._stop_event.clear()

        # Auslagerung in einen Hintergrund-Thread, um UI-Freezes zu verhindern
        def _watch():
            attempts = 0
            while attempts < 300 and not self._stop_event.is_set():
                current_hash = calculate_md5(self.project_path)
                if current_hash == expected_hash:
                    logging.info("[Sync] Download/Sync erfolgreich.")
                    EventBus.emit("SYNC_DOWNLOAD_COMPLETED", data={"success": True})
                    return
                time.sleep(1)
                attempts += 1

            if not self._stop_event.is_set():
                logging.warning("[Sync] Download Timeout!")
                EventBus.emit("SYNC_DOWNLOAD_COMPLETED", data={"success": False})

        threading.Thread(target=_watch, daemon=True).start()