# ================================================
# FILE: services/system_monitor_service.py
# ================================================
import time
import threading
import logging
from core.event_bus import EventBus
from services.daws import get_current_daw
from services.base_service import BaseService

class SystemMonitorService(BaseService):
    def __init__(self):
        super().__init__()
        self._running = False
        self.state = "WAITING_FOR_CLOSE"
        self._thread = None
        self.daw = get_current_daw()
        self.register_listeners()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logging.info("[SystemMonitor] Hintergrund-Überwachung gestartet.")

    def stop(self):
        self._running = False
        self.cleanup()

    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
            logging.debug(f"[SystemMonitor] Statuswechsel zu: {new_state}")
            EventBus.clear_history()

    def _loop(self):
        while self._running:
            if self.state in ["GAME_RUNNING", "FINISH"]:
                EventBus.emit_distinct("SYS_FL_WARNING_HIDE")
                time.sleep(1.0)
            elif self.state == "WAITING_FOR_CLOSE":
                if self.daw.is_running():
                    EventBus.emit_distinct("SYS_FL_WARNING_SHOW")
                else:
                    EventBus.emit_distinct("SYS_FL_WARNING_HIDE")
                    self.state = "LOCKED"
                time.sleep(0.5)
            elif self.state == "LOCKED":
                if self.daw.kill_all_instances():
                    EventBus.emit("SYS_FL_MANUAL_START_BLOCKED")
                time.sleep(0.2)