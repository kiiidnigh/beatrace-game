import time
import threading
import psutil
from pynput import mouse
from utils.process import is_fl_running, get_active_window_title, force_save_and_close_fl, FL_PROCESS_NAME


class FLWatcher:
    def __init__(self):
        self._is_monitoring = False
        self._monitor_thread = None

    def wait_for_start(self, callback):
        self.stop()
        self._is_monitoring = True

        def loop():
            while self._is_monitoring:
                if is_fl_running():
                    self._is_monitoring = False
                    if callback: callback()
                    return
                time.sleep(0.5)

        self._monitor_thread = threading.Thread(target=loop, daemon=True)
        self._monitor_thread.start()

    def wait_for_interaction(self, callback):
        self.stop()
        self._is_monitoring = True

        def loop():
            def on_click(x, y, button, pressed):
                if pressed and self._is_monitoring:
                    # FIX: Windows 50ms Zeit geben, um FL Studio in den Vordergrund zu holen
                    time.sleep(0.05)
                    if "fl studio" in get_active_window_title():
                        self._is_monitoring = False
                        if callback: callback()
                        return False

            with mouse.Listener(on_click=on_click) as listener:
                while self._is_monitoring and listener.running:
                    time.sleep(0.1)
                if not self._is_monitoring and listener.running:
                    listener.stop()

        self._monitor_thread = threading.Thread(target=loop, daemon=True)
        self._monitor_thread.start()

    def wait_for_exit(self, callback):
        self.stop()
        self._is_monitoring = True

        def loop():
            target_proc = None

            while self._is_monitoring and not target_proc:
                for p in psutil.process_iter(['name']):
                    try:
                        if p.info['name'] and p.info['name'].lower() == FL_PROCESS_NAME:
                            target_proc = p
                            break
                    except:
                        pass
                if not target_proc:
                    time.sleep(0.5)

            if target_proc:
                while self._is_monitoring and target_proc.is_running():
                    time.sleep(0.1)

            if self._is_monitoring:
                self._is_monitoring = False
                if callback: callback()

        self._monitor_thread = threading.Thread(target=loop, daemon=True)
        self._monitor_thread.start()

    def auto_save_and_close(self):
        """Versucht FL Studio sauber mit Auto-Save zu beenden."""

        def run():
            force_save_and_close_fl()

            # Fail-Safe Überprüfung nach 5 Sekunden
            time.sleep(5)
            if is_fl_running():
                import logging
                logging.warning("Auto-Save konnte FL Studio nicht beenden!")

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._is_monitoring = False