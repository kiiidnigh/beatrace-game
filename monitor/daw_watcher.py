# ================================================
# FILE: monitor/daw_watcher.py
# ================================================
import time
import threading
import psutil
from pynput import mouse
from services.daws import get_current_daw


class DAWWatcher:
    def __init__(self):
        self._monitoring_start = False
        self._monitoring_interaction = False
        self._monitoring_exit = False
        self._mouse_listener = None

        # OCP: Wir holen uns die aktuell aktive DAW
        self.daw = get_current_daw()

    def wait_for_start(self, callback):
        self._monitoring_start = True

        def loop():
            while self._monitoring_start:
                if self.daw.is_running():
                    self._monitoring_start = False
                    if callback: callback()
                    return
                time.sleep(0.5)

        threading.Thread(target=loop, daemon=True).start()

    def wait_for_interaction(self, callback):
        self._monitoring_interaction = True

        def loop():
            def on_click(x, y, button, pressed):
                if pressed and self._monitoring_interaction:
                    self._monitoring_interaction = False
                    if callback: callback()
                    return False  # Beendet den Listener intern sofort

            self._mouse_listener = mouse.Listener(on_click=on_click)
            self._mouse_listener.start()

            while self._monitoring_interaction and self._mouse_listener.is_alive():
                time.sleep(0.1)

            if self._mouse_listener and self._mouse_listener.is_alive():
                self._mouse_listener.stop()

            self._mouse_listener = None

        threading.Thread(target=loop, daemon=True).start()

    def wait_for_exit(self, callback):
        self._monitoring_exit = True

        def loop():
            target_proc = None

            while self._monitoring_exit and not target_proc:
                for p in psutil.process_iter(['name']):
                    try:
                        if p.info['name'] and p.info['name'].lower() == self.daw.process_name:
                            target_proc = p
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                if not target_proc:
                    time.sleep(0.5)

            if target_proc:
                while self._monitoring_exit and target_proc.is_running():
                    time.sleep(0.2)

            if self._monitoring_exit:
                self._monitoring_exit = False
                if callback: callback()

        threading.Thread(target=loop, daemon=True).start()

    def auto_save_and_close(self):
        def run():
            self.daw.force_save_and_close()
            time.sleep(5)
            if self.daw.is_running():
                import logging
                logging.warning(f"[DAWWatcher] Auto-Save konnte {self.daw.name} nicht beenden!")

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._monitoring_start = False
        self._monitoring_interaction = False
        self._monitoring_exit = False

        if self._mouse_listener and self._mouse_listener.is_alive():
            self._mouse_listener.stop()
            self._mouse_listener = None