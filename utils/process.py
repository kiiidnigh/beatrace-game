import psutil
import time
import ctypes
import logging

FL_PROCESS_NAME = "fl64.exe"
WM_CLOSE = 0x0010
VK_RETURN = 0x0D  # Windows Hex-Code für die ENTER-Taste
KEYEVENTF_KEYUP = 0x0002


def get_active_window_title():
    """Liest den Titel des aktuell fokussierten Fensters in Windows aus."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.lower()
    except Exception as e:
        logging.warning(f"[ProcessUtil] Fehler beim Lesen des Fenster-Titels: {e}")
        return ""


def is_fl_running():
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == FL_PROCESS_NAME:
                return True
        except:
            pass
    return False

def kill_all_fl_instances():
    """Beendet alle laufenden FL Studio Prozesse (z.B. als Cleanup beim Start)."""
    killed_any = False
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == FL_PROCESS_NAME:
                proc.kill()
                killed_any = True
        except:
            pass
    return killed_any

def force_save_and_close_fl():
    """
    Der ultimative Auto-Save!
    Triggert den Schließen-Dialog, wartet dynamisch auf das Fenster und sendet einen ENTER-Tastendruck.
    """
    logging.info("[ProcessUtil] Initiiere Auto-Save und Schließen...")
    fl_pids = set()
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == FL_PROCESS_NAME:
                fl_pids.add(proc.info['pid'])
        except:
            pass

    if not fl_pids:
        logging.debug("[ProcessUtil] Keine laufende FL Studio Instanz gefunden.")
        return False

    main_hwnd = None

    # 1. Hauptfenster finden
    def find_main_window(hwnd, _):
        nonlocal main_hwnd
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            owner = ctypes.windll.user32.GetWindow(hwnd, 4)  # GW_OWNER
            if owner == 0:
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in fl_pids:
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    buf = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                    if "fl studio" in buf.value.lower():
                        main_hwnd = hwnd
                        return False  # Stoppt die Suche
        return True

    ctypes.windll.user32.EnumWindows(
        ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(find_main_window), 0)

    if main_hwnd:
        # FL Studio Hauptfenster in den Vordergrund zwingen
        ctypes.windll.user32.SetForegroundWindow(main_hwnd)
        time.sleep(0.1)

        # 2. Dem Hauptfenster sagen: "Schließ dich!" (Triggert den Dialog)
        ctypes.windll.user32.PostMessageW(main_hwnd, WM_CLOSE, 0, 0)

        # 3. Dynamisch auf den Dialog warten (Max 2 Sekunden Timeout)
        for _ in range(20):
            time.sleep(0.1)

            # Wenn FL Studio sofort zugeht (weil keine Änderungen gemacht wurden), perfekt!
            if not is_fl_running():
                logging.info("[ProcessUtil] FL Studio erfolgreich ohne Speicherdialog geschlossen.")
                return True

            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            # Wenn das fokussierte Fenster zu FL gehört UND NICHT das Hauptfenster ist = Es ist der Dialog!
            if pid.value in fl_pids and hwnd != main_hwnd:
                time.sleep(0.2)  # Dem Dialog kurz 200ms geben, um den "Ja" Button final zu fokussieren

                # 4. Sende den "ENTER" Tastendruck (Hardware-Ebene)
                logging.info("[ProcessUtil] Speicher-Dialog erkannt. Sende ENTER Key...")
                ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)  # Taste Runter
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)  # Taste Hoch
                return True

    logging.warning("[ProcessUtil] Konnte FL Studio nicht automatisch schließen.")
    return False