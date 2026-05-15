# ================================================
# FILE: utils/os_utils.py
# ================================================
import os
import platform
import threading
import tempfile
import subprocess

if platform.system() == "Windows":
    import ctypes
    import winsound


    class FLASHWINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint),
                    ("hwnd", ctypes.c_void_p),
                    ("dwFlags", ctypes.c_uint),
                    ("uCount", ctypes.c_uint),
                    ("dwTimeout", ctypes.c_uint)]


def play_alert_sound(sound_type="warning"):
    """
    Spielt den nativen Windows-Systemsound ab, ohne das UI zu blockieren.
    """
    if platform.system() != "Windows":
        return

    flags = {
        "warning": winsound.MB_ICONWARNING,
        "error": winsound.MB_ICONHAND,
        "info": winsound.MB_ICONASTERISK,
        "ok": winsound.MB_OK
    }
    flag = flags.get(sound_type, winsound.MB_ICONWARNING)

    threading.Thread(target=lambda: winsound.MessageBeep(flag), daemon=True).start()


def flash_window_taskbar(hwnd):
    """
    Lässt das Fenster in der Windows-Taskleiste orange blinken.
    """
    if platform.system() != "Windows" or not hwnd:
        return

    try:
        # GA_ROOT (2) zwingt Windows, den absoluten "Root"-Rahmen des Fensters zu finden,
        # der auch tatsächlich mit dem Taskleisten-Icon verknüpft ist.
        GA_ROOT = 2
        root_hwnd = ctypes.windll.user32.GetAncestor(int(hwnd), GA_ROOT)

        info = FLASHWINFO()
        info.cbSize = ctypes.sizeof(FLASHWINFO)
        info.hwnd = root_hwnd
        # 3 (FLASHW_ALL) + 12 (FLASHW_TIMERNOFG) = 15
        # Das bedeutet: Taskleiste flashen, bis der Nutzer das Fenster in den Fokus holt.
        info.dwFlags = 15
        info.uCount = 0
        info.dwTimeout = 0

        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    except Exception as e:
        import logging
        logging.debug(f"[OSUtils] Fehler beim Flashen des Fensters: {e}")


def extract_exe_icon(exe_path):
    """
    Extrahiert das native Icon einer ausführbaren Windows-Datei ohne schwere Bibliotheken (KISS Prinzip).
    Verwendet dafür einen schnellen PowerShell-Befehl aus den Windows Bordmitteln.
    """
    if platform.system() != "Windows" or not os.path.exists(exe_path):
        return None

    try:
        from PIL import Image
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, "extracted_app_icon.png")

        # SoC: Nutze das .NET Framework über PowerShell für die saubere, systemeigene Extraktion
        ps_script = f"""
        Add-Type -AssemblyName System.Drawing;
        $icon = [System.Drawing.Icon]::ExtractAssociatedIcon('{exe_path}');
        $bit = $icon.ToBitmap();
        $bit.Save('{out_path}', [System.Drawing.Imaging.ImageFormat]::Png);
        """

        # Blockierend, aber mit ganz kurzem Timeout (Fail Fast)
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script],
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=3)

        if os.path.exists(out_path):
            img = Image.open(out_path).copy()  # Bild in RAM kopieren, um die Datei freizugeben
            os.remove(out_path)
            return img

    except Exception as e:
        import logging
        logging.error(f"[OSUtils] Fehler beim Extrahieren des Icons: {e}")

    return None