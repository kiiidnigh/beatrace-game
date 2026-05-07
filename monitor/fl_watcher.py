import time
import threading
import psutil
from pynput import mouse
from utils.process import is_fl_running, force_save_and_close_fl, FL_PROCESS_NAME


class FLWatcher:
    def __init__(self):
        self._monitoring_start = False
        self._monitoring_interaction = False
        self._monitoring_exit = False
        # FIX: Referenz auf den Listener speichern, um Memory Leaks zu verhindern
        self._mouse_listener = None

    def wait_for_start(self, callback):
        self._monitoring_start = True

        def loop():
            while self._monitoring_start:
                if is_fl_running():
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

            # Warten, bis Überwachung abgebrochen wird oder Listener stirbt
            while self._monitoring_interaction and self._mouse_listener.is_alive():
                time.sleep(0.1)

            # Fail-Safe: Wenn die Überwachung von außen abgebrochen wird, Listener killen
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
                        if p.info['name'] and p.info['name'].lower() == FL_PROCESS_NAME:
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
        """Versucht FL Studio sauber mit Auto-Save zu beenden."""

        def run():
            force_save_and_close_fl()
            # Fail-Safe Überprüfung nach 5 Sekunden
            time.sleep(5)
            if is_fl_running():
                import logging
                logging.warning("[FLWatcher] Auto-Save konnte FL Studio nicht beenden!")

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        """Stoppt alle Überwachungen sofort."""
        self._monitoring_start = False
        self._monitoring_interaction = False
        self._monitoring_exit = False

        if self._mouse_listener and self._mouse_listener.is_alive():
            self._mouse_listener.stop()
            self._mouse_listener = None