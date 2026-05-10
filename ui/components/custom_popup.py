# ================================================
# FILE: ui/components/custom_popup.py
# ================================================
import customtkinter as ctk
import platform
from utils.ui_utils import get_centered_geometry
from utils.os_utils import play_alert_sound, flash_window_taskbar


class CustomPopup(ctk.CTkToplevel):
    """
    Ein universelles, modales Popup, das sich nativ wie eine Windows-Warnung verhält
    (Sound + Taskleisten-Blinken), aber im Design der App bleibt.
    """

    def __init__(self, master, title, message, icon="ℹ️", btn_color="#3a7ebf", sound_type="info",
                 on_close_callback=None):
        super().__init__(master)

        self.master_ref = master

        self.title(title)
        self.attributes('-topmost', True)
        self.resizable(False, False)

        # Modales Verhalten erzwingen
        self.transient(master)
        self.grab_set()

        self.geometry(get_centered_geometry(master, width=400, height=250))

        self.on_close_callback = on_close_callback
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # UI Aufbau
        ctk.CTkLabel(self, text=icon, font=("Helvetica", 40)).pack(pady=(20, 0))
        ctk.CTkLabel(self, text=message, font=("Helvetica", 14), justify="center", wraplength=350).pack(pady=(10, 20),
                                                                                                        padx=20)
        ctk.CTkButton(self, text="OK", width=120, command=self._on_close, fg_color=btn_color).pack(pady=(0, 20))

        # Windows-Effekte mit leichter Verzögerung auslösen, damit das UI erst fertig rendert
        self.after(100, lambda: self._trigger_native_alerts(sound_type))

    def _trigger_native_alerts(self, sound_type):
        """Zieht die maximale Aufmerksamkeit des Nutzers auf das Fenster."""
        # 1. Nativen Windows Sound abspielen
        play_alert_sound(sound_type)

        # 2. Die Taskleiste zum Blinken bringen
        if platform.system() == "Windows":
            try:
                # wm_frame() gibt uns zuverlässiger den OS-Rahmen als winfo_id()
                hwnd_str = self.master_ref.wm_frame()
                hwnd = int(hwnd_str, 16)
            except Exception:
                # Fallback, falls wm_frame scheitert
                hwnd = self.master_ref.winfo_id()

            flash_window_taskbar(hwnd)

        # 3. Fenster in den Vordergrund zwingen
        # WICHTIG: Wenn Windows diesen Befehl zulässt und wir erfolgreich den Fokus stehlen,
        # hört das Blinken aus Schritt 2 sofort wieder auf (das ist das korrekte Windows-Verhalten!).
        # Wenn wir den Fokus nicht stehlen dürfen (z.B. weil der Nutzer gerade in FL Studio klickt),
        # blinkt die Taskleiste weiter, bis er Beatrace anklickt.
        self.lift()
        self.focus_force()

    def _on_close(self):
        self.destroy()
        if self.on_close_callback:
            self.on_close_callback()