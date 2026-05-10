# ================================================
# FILE: ui/components/custom_popup.py
# ================================================
import customtkinter as ctk
import platform
from utils.ui_utils import get_centered_geometry
from utils.os_utils import play_alert_sound, flash_window_taskbar


class CustomPopup(ctk.CTkToplevel):
    """
    Ein universelles, modales Popup, das sich nativ wie eine Windows-Warnung verhält.
    Unterstützt jetzt auch Ja/Nein Entscheidungen.
    """

    def __init__(self, master, title, message, icon="ℹ️", btn_color="#3a7ebf", sound_type="info",
                 show_cancel=False, confirm_text="OK", cancel_text="Abbrechen",
                 on_confirm_callback=None, on_cancel_callback=None):
        super().__init__(master)

        self.master_ref = master
        self.on_confirm_callback = on_confirm_callback
        self.on_cancel_callback = on_cancel_callback

        self.title(title)
        self.attributes('-topmost', True)
        self.resizable(False, False)

        self.transient(master)
        self.grab_set()

        self.geometry(get_centered_geometry(master, width=400, height=250))

        # Standard Schließen via X (wird wie Cancel behandelt)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # UI Aufbau
        ctk.CTkLabel(self, text=icon, font=("Helvetica", 40)).pack(pady=(20, 0))
        ctk.CTkLabel(self, text=message, font=("Helvetica", 14), justify="center", wraplength=350).pack(pady=(10, 20),
                                                                                                        padx=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        if show_cancel:
            ctk.CTkButton(btn_frame, text=confirm_text, width=120, command=self._on_confirm, fg_color=btn_color).pack(
                side="left", padx=10)
            ctk.CTkButton(btn_frame, text=cancel_text, width=120, command=self._on_cancel, fg_color="#636E72",
                          hover_color="#2D3436").pack(side="left", padx=10)
        else:
            ctk.CTkButton(btn_frame, text=confirm_text, width=120, command=self._on_confirm, fg_color=btn_color).pack()

        self.after(100, lambda: self._trigger_native_alerts(sound_type))

    def _trigger_native_alerts(self, sound_type):
        play_alert_sound(sound_type)
        if platform.system() == "Windows":
            try:
                hwnd_str = self.master_ref.wm_frame()
                hwnd = int(hwnd_str, 16)
            except Exception:
                hwnd = self.master_ref.winfo_id()

            flash_window_taskbar(hwnd)

        self.lift()
        self.focus_force()

    def _on_confirm(self):
        self.grab_release()
        self.destroy()
        if self.on_confirm_callback:
            self.on_confirm_callback()

    def _on_cancel(self):
        self.grab_release()
        self.destroy()
        if self.on_cancel_callback:
            self.on_cancel_callback()