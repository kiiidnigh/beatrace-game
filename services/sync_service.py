import os
import time
import threading
import logging
from monitor.file_watcher import FileWatcher
from utils.file_utils import calculate_md5
from core.event_bus import EventBus


class SyncService:
    def __init__(self, project_path):
        self.project_path = project_path
        self.drive_watcher = FileWatcher(self.project_path)
        logging.info("[SyncService] Bereit fuer Dateiueberwachung.")
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        EventBus.subscribe("CMD_WAIT_FOR_LOCK", self._handle_wait_lock)
        EventBus.subscribe("CMD_WATCH_DOWNLOAD", self._handle_watch_download)
        EventBus.subscribe("CMD_STOP_SYNC_MONITOR", lambda d: self.drive_watcher.stop())

    def _handle_wait_lock(self, data):
        max_attempts = data.get("max_attempts", 100)
        logging.info("[SyncService] Warte auf Freigabe der Projektdatei...")
        threading.Thread(target=self._wait_lock_thread, args=(max_attempts,), daemon=True).start()

    def _wait_lock_thread(self, max_attempts):
        attempts = 0
        while attempts <= max_attempts:
            try:
                if os.path.exists(self.project_path):
                    os.rename(self.project_path, self.project_path)  # Testet ob gelockt
                time.sleep(0.2)
                file_hash = calculate_md5(self.project_path)
                logging.info("[SyncService] Datei frei! Sende Hash an EventBus.")
                EventBus.emit("SYNC_LOCK_RELEASED", data={"hash": file_hash})
                return
            except OSError:
                attempts += 1
                time.sleep(0.1)

        logging.error(f"[SyncService] Timeout beim Warten auf Datei: {self.project_path}")
        EventBus.emit("SYNC_LOCK_TIMEOUT")

    def _handle_watch_download(self, data):
        expected_hash = data.get("expected_hash")
        logging.info(f"[SyncService] Ueberwache Download. Erwarteter Hash: {expected_hash}")
        self.drive_watcher.file_path = self.project_path
        self.drive_watcher.wait_for_sync_complete(
            expected_hash=expected_hash,
            callback=lambda success: EventBus.emit("SYNC_DOWNLOAD_COMPLETED", data={"success": success})
        )