# ================================================
# FILE: services/sync_service.py
# ================================================
import os
import time
import threading
import logging
from utils.file_utils import calculate_md5
from core.event_bus import EventBus
from core.events import CmdEvents, SysEvents, UIEvents
from services.base_service import BaseService
from services.storage.base_adapter import BaseStorageAdapter, SyncException

class SyncService(BaseService):
    def __init__(self, local_path: str, remote_path: str, storage_adapter: BaseStorageAdapter):
        super().__init__()
        self.local_path = local_path
        self.remote_path = remote_path

        # Law of Demeter: Der Service kennt nur das Interface, nicht Rclone selbst.
        self.storage = storage_adapter
        self._stop_event = threading.Event()

        self._listeners = {
            CmdEvents.WAIT_FOR_LOCK: self._handle_upload,
            CmdEvents.WATCH_DOWNLOAD: self._handle_download,
            CmdEvents.STOP_SYNC_MONITOR: lambda d: self._stop_event.set()
        }
        self.register_listeners()

    def cleanup(self):
        self._stop_event.set()
        super().cleanup()

    def _handle_upload(self, data):
        max_attempts = data.get("max_attempts", 100)
        self._stop_event.clear()

        def _task():
            attempts = 0
            released = False

            # 1. Warten, bis die DAW die Datei auf der Festplatte freigibt
            while attempts < max_attempts and not self._stop_event.is_set():
                if os.path.exists(self.local_path):
                    try:
                        os.rename(self.local_path, self.local_path)
                        released = True
                        break
                    except OSError:
                        pass
                time.sleep(0.5)
                attempts += 1

            if not released and not self._stop_event.is_set():
                logging.warning("[Sync] Timeout beim Warten auf Dateifreigabe.")
                EventBus.emit("SYNC_LOCK_TIMEOUT")
                return

            # 2. Direkter Upload per Rclone (Kein Polling mehr!)
            if not self._stop_event.is_set():
                try:
                    EventBus.emit(UIEvents.STATUS_UPDATE, data={"text": "Lade in die Cloud hoch...", "color": "yellow"})

                    self.storage.upload(self.local_path, self.remote_path)
                    file_hash = calculate_md5(self.local_path)

                    logging.info(f"[Sync] Upload erfolgreich. Hash: {file_hash}")
                    EventBus.emit(SysEvents.SYNC_SUCCESS)
                    EventBus.emit("SYNC_LOCK_RELEASED", data={"hash": file_hash})

                except SyncException as e:
                    logging.error(f"[Sync] Upload fehlgeschlagen: {e}")
                    EventBus.emit(SysEvents.SYNC_ERROR, data={"error": str(e)})
                    EventBus.emit("SYNC_LOCK_TIMEOUT")

        threading.Thread(target=_task, daemon=True).start()

    def _handle_download(self, data):
        # Wenn kein Sync erwartet wird (z.B. Spieler hat aufgegeben), brechen wir den Download SOFORT ab!
        if not data.get("expected_to_sync", True):
            return

        expected_hash = data.get("expected_hash")
        self._stop_event.clear()

        def _task():
            if self._stop_event.is_set(): return

            try:
                EventBus.emit(UIEvents.STATUS_UPDATE,
                              data={"text": "Lade aus der Cloud herunter...", "color": "yellow"})

                # 1. Direkter Download per Rclone (Fail Fast)
                self.storage.download(self.remote_path, self.local_path)

                # 2. Hash Validierung
                if expected_hash:
                    current_hash = calculate_md5(self.local_path)
                    if current_hash != expected_hash:
                        logging.warning(
                            f"[Sync] Checksummen Warnung! Erwartet: {expected_hash}, Bekommen: {current_hash}")

                logging.info("[Sync] Download erfolgreich.")
                EventBus.emit(SysEvents.SYNC_SUCCESS)
                EventBus.emit("SYNC_DOWNLOAD_COMPLETED", data={"success": True})

            except SyncException as e:
                logging.error(f"[Sync] Download fehlgeschlagen: {e}")
                EventBus.emit(SysEvents.SYNC_ERROR, data={"error": str(e)})
                EventBus.emit("SYNC_DOWNLOAD_COMPLETED", data={"success": False})

        threading.Thread(target=_task, daemon=True).start()