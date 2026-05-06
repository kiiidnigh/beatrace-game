import customtkinter as ctk


class ToastNotification(ctk.CTkToplevel):
    def __init__(self, message, color="#1DB954", duration=4000):
        super().__init__()
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#2D3436")

        # Berechne Position (unten rechts)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = 300
        height = 60
        x = screen_width - width - 20
        y = screen_height - height - 60

        self.geometry(f"{width}x{height}+{x}+{y}")

        self.lbl = ctk.CTkLabel(self, text=message, font=("Helvetica", 14, "bold"), text_color=color)
        self.lbl.pack(expand=True)

        # Wenn duration > 0, schliesst sich das Fenster automatisch
        if duration > 0:
            self.after(duration, self.destroy)

    def update_text(self, text):
        """Erlaubt es, den Text live zu aendern (fuer Countdowns)."""
        self.lbl.configure(text=text)