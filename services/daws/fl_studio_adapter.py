# ================================================
# FILE: services/daws/fl_studio_adapter.py
# ================================================
import os
import time
import ctypes
import logging
import psutil
import string
from .base_adapter import BaseDAWAdapter
from utils.file_utils import load_prefs, save_prefs


class FLStudioAdapter(BaseDAWAdapter):
    def __init__(self):
        self._process_name = "fl64.exe"
        self._executable_path = None

    @property
    def name(self):
        return "FL Studio"

    @property
    def process_name(self):
        return self._process_name

    @property
    def executable_path(self):
        prefs = load_prefs()
        saved_path = prefs.get("fl_studio_path", "")

        # 1. SoC: Bevorzuge immer die manuelle Usereingabe aus den Settings
        if saved_path and os.path.exists(saved_path):
            self._executable_path = saved_path
            return self._executable_path

        # 2. Fallback: Starte die verbesserte, robuste automatische Suche
        if not self._executable_path or not os.path.exists(self._executable_path):
            self._executable_path = self._find_executable()
            # Wenn gefunden, speichern wir es, damit nicht jedes Mal gesucht werden muss
            if self._executable_path:
                prefs["fl_studio_path"] = self._executable_path
                save_prefs(prefs)

        return self._executable_path

    def _find_executable(self):
        """Sucht extrem robust in allen Image-Line Verzeichnissen nach der DAW."""
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        search_folders = ["Program Files", "Program Files (x86)", ""]

        # Wir suchen nach verschiedenen Ausführungen der Executable
        exe_names = ["FL64.exe", "FL.exe", "fl64.exe", "fl.exe"]

        for drive in drives:
            for sub_folder in search_folders:
                base_path = os.path.join(drive, sub_folder, "Image-Line")

                if os.path.exists(base_path):
                    try:
                        # Wir sortieren rückwärts, damit neuere Versionen (z.B. Ordner "FL Studio 24" vs "FL Studio 20")
                        # zuerst geprüft werden, falls der User mehrere FL Versionen installiert hat.
                        subdirs = sorted(os.listdir(base_path), reverse=True)

                        for folder in subdirs:
                            folder_path = os.path.join(base_path, folder)
                            if os.path.isdir(folder_path):
                                # Prüfe auf alle möglichen Executable-Namen in diesem Ordner (Kein fehleranfälliger Namens-Check des Ordners mehr!)
                                for exe_name in exe_names:
                                    exe_path = os.path.join(folder_path, exe_name)
                                    if os.path.exists(exe_path):
                                        logging.info(f"[FLStudioAdapter] Automatisch gefunden: {exe_path}")
                                        return exe_path
                    except PermissionError:
                        pass  # Systemordner ignorieren (Fail Fast & Recover)

        logging.warning("[FLStudioAdapter] FL Studio konnte auf keinem Laufwerk gefunden werden.")
        return None

    def is_running(self):
        for proc in psutil.process_iter(['name']):
            try:
                # Prüfe dynamisch gegen den Namen der gefundenen Exe, nicht starr "fl64.exe"
                target_name = os.path.basename(
                    self.executable_path).lower() if self.executable_path else self.process_name
                if proc.info['name'] and proc.info['name'].lower() == target_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def kill_all_instances(self):
        killed_any = False
        target_name = os.path.basename(self.executable_path).lower() if self.executable_path else self.process_name

        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == target_name:
                    proc.kill()
                    killed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return killed_any

    def force_save_and_close(self):
        """Der FL Studio spezifische Auto-Save Hack via Windows API."""
        logging.info("[FLStudioAdapter] Initiiere Auto-Save und Schließen...")
        WM_CLOSE = 0x0010
        VK_RETURN = 0x0D
        KEYEVENTF_KEYUP = 0x0002

        target_name = os.path.basename(self.executable_path).lower() if self.executable_path else self.process_name

        fl_pids = set()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == target_name:
                    fl_pids.add(proc.info['pid'])
            except:
                pass

        if not fl_pids:
            return False

        main_hwnd = None

        def find_main_window(hwnd, _):
            nonlocal main_hwnd
            if ctypes.windll.user32.IsWindowVisible(hwnd):
                owner = ctypes.windll.user32.GetWindow(hwnd, 4)
                if owner == 0:
                    pid = ctypes.c_ulong()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value in fl_pids:
                        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        if "fl studio" in buf.value.lower():
                            main_hwnd = hwnd
                            return False
            return True

        ctypes.windll.user32.EnumWindows(
            ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(find_main_window), 0)

        if main_hwnd:
            ctypes.windll.user32.SetForegroundWindow(main_hwnd)
            time.sleep(0.1)
            ctypes.windll.user32.PostMessageW(main_hwnd, WM_CLOSE, 0, 0)

            for _ in range(20):
                time.sleep(0.1)
                if not self.is_running():
                    return True

                hwnd = ctypes.windll.user32.GetForegroundWindow()
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

                if pid.value in fl_pids and hwnd != main_hwnd:
                    time.sleep(0.2)
                    logging.info("[FLStudioAdapter] Speicher-Dialog erkannt. Sende ENTER Key...")
                    ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
                    time.sleep(0.05)
                    ctypes.windll.user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
                    return True

        return False