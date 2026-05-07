import time
import threading
import logging
from utils.process import is_fl_running, kill_all_fl_instances
from core.event_bus import EventBus


class SystemMonitorService:
    """
    Überwacht das Betriebssystem unabhängig vom UI.
    Passt auf, dass FL Studio geschlossen bleibt, bis das eigentliche Match startet.
    """

    def __init__(self):
        self._running = False
        self.state = "WAITING_FOR_CLOSE"
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logging.info("[SystemMonitor] Hintergrund-Überwachung gestartet.")

    def stop(self):
        self._running = False

    def set_state(self, new_state):
        """Erlaubt der GameView/MainWindow den Status des Wachhunds zu ändern."""
        if self.state != new_state:
            self.state = new_state
            logging.debug(f"[SystemMonitor] Statuswechsel zu: {new_state}")
            # Historie löschen, damit ein Wechsel sofort wieder saubere Events erlaubt
            EventBus.clear_history()

    def _loop(self):
        while self._running:
            if self.state in ["GAME_RUNNING", "FINISH"]:
                # Nutzt emit_distinct -> Loggt und feuert exakt nur 1x
                EventBus.emit_distinct("SYS_FL_WARNING_HIDE")
                time.sleep(1.0)

            elif self.state == "WAITING_FOR_CLOSE":
                if is_fl_running():
                    EventBus.emit_distinct("SYS_FL_WARNING_SHOW")
                else:
                    EventBus.emit_distinct("SYS_FL_WARNING_HIDE")
                    self.state = "LOCKED"
                time.sleep(0.5)

            elif self.state == "LOCKED":
                if kill_all_fl_instances():
                    # Hier bleibt das normale emit, weil es ja wirklich ein neues Ereignis
                    # ist, wenn der Nutzer versucht, FL manuell zu öffnen!
                    EventBus.emit("SYS_FL_MANUAL_START_BLOCKED")
                time.sleep(0.2)