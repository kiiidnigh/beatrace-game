# ================================================
# FILE: ui/components/toast.py
# ================================================
import customtkinter as ctk
from utils.ui_utils import get_bottom_right_geometry

class ToastNotification(ctk.CTkToplevel):
    def __init__(self, master, message, color="#1DB954", duration=4000):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#2D3436")

        # FIX 2: Nutzt nun die Positionierung unten rechts im Bildschirm!
        self.geometry(get_bottom_right_geometry(
            width=300,
            height=60,
            screen_width=self.winfo_screenwidth(),
            screen_height=self.winfo_screenheight()
        ))

        self.lbl = ctk.CTkLabel(self, text=message, font=("Helvetica", 14, "bold"), text_color=color)
        self.lbl.pack(expand=True)

        if duration > 0:
            self.after(duration, self.destroy)

    def update_text(self, text):
        self.lbl.configure(text=text)