# ================================================
# FILE: utils/os_utils.py
# ================================================
import platform
import threading

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
        import ctypes

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