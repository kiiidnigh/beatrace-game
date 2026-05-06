import customtkinter as ctk
from utils.file_utils import load_prefs, save_prefs


class SettingsModal(ctk.CTkToplevel):
    def __init__(self, master, on_save_callback=None):
        super().__init__(master)
        self.title("App Einstellungen")
        self.geometry("400x350")
        self.attributes('-topmost', True)
        self.resizable(False, False)

        self.on_save_callback = on_save_callback
        self.prefs = load_prefs()

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="UX Modus (während deines Zuges)", font=("Helvetica", 16, "bold")).pack(pady=(20, 10))

        self.mode_var = ctk.StringVar(value=self.prefs.get("ui_mode", "Standard"))

        modes = [
            ("Standard", "Das normale Fenster bleibt offen."),
            ("Mini-Player", "Schwebendes, kleines Widget über FL Studio."),
            ("Stealth", "Fenster wird unsichtbar. Benachrichtigungen\nunten rechts. Pause via STRG+SHIFT+P.")
        ]

        for mode, desc in modes:
            frame = ctk.CTkFrame(self, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=5)

            rb = ctk.CTkRadioButton(frame, text=mode, variable=self.mode_var, value=mode,
                                    font=("Helvetica", 14, "bold"))
            rb.pack(anchor="w")

            ctk.CTkLabel(frame, text=desc, font=("Helvetica", 12), text_color="gray", justify="left").pack(anchor="w",
                                                                                                           padx=25)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20, side="bottom")

        ctk.CTkButton(btn_frame, text="Speichern", fg_color="#1DB954", hover_color="#14833b",
                      command=self.save_and_close).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Abbrechen", fg_color="#c0392b", hover_color="#e74c3c",
                      command=self.destroy).pack(side="left", padx=10)

    def save_and_close(self):
        self.prefs["ui_mode"] = self.mode_var.get()
        save_prefs(self.prefs)
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()