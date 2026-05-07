import customtkinter as ctk
import logging
from utils.file_utils import load_prefs, save_prefs
from core.event_bus import EventBus


class MiniPlayer(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        logging.debug("[MiniPlayer] Initialisiere MiniPlayer Widget...")

        self.prefs = load_prefs()
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#1e1e1e")

        # Lade die letzte gespeicherte Position oder nutze Standardwerte
        last_x = self.prefs.get("mini_player_x", 100)
        last_y = self.prefs.get("mini_player_y", 100)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        if last_x > screen_w - 300 or last_x < 0: last_x = 100
        if last_y > screen_h - 80 or last_y < 0: last_y = 100

        self.geometry(f"300x80+{last_x}+{last_y}")

        self._x = 0
        self._y = 0

        self.setup_ui()
        self.bind_drag()

    def setup_ui(self):
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10)

        drag_lbl = ctk.CTkLabel(info_frame, text="[=]", text_color="gray", cursor="fleur")
        drag_lbl.pack(side="left", padx=(0, 10))

        text_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=10)

        self.lbl_player = ctk.CTkLabel(text_frame, text="Status", font=("Helvetica", 12), text_color="#1DB954",
                                       anchor="w")
        self.lbl_player.pack(fill="x")

        self.lbl_time = ctk.CTkLabel(text_frame, text="Warte auf Klick...", font=("Helvetica", 16, "bold"), anchor="w")
        self.lbl_time.pack(fill="x")

        # Der Button sendet weiterhin den Befehl, wird aber visuell strikt als Pause-Button genutzt
        self.btn_pause = ctk.CTkButton(self, text="||", width=40, height=40, state="disabled",
                                       command=lambda: EventBus.emit("CMD_TOGGLE_PAUSE"))
        self.btn_pause.pack(side="right", padx=10)

    def bind_drag(self):
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<ButtonRelease-1>", self.stop_move)
        self.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def stop_move(self, event):
        self._x = None
        self._y = None
        self.prefs["mini_player_x"] = self.winfo_x()
        self.prefs["mini_player_y"] = self.winfo_y()
        save_prefs(self.prefs)
        logging.debug(f"[MiniPlayer] Position gespeichert: X={self.winfo_x()}, Y={self.winfo_y()}")

    def do_move(self, event):
        deltax = event.x - self._x
        deltay = event.y - self._y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def update_status(self, text, is_warning=False):
        self.lbl_player.configure(text="System")
        self.btn_pause.configure(state="disabled")
        color = "yellow" if is_warning else "white"

        font_size = 12 if len(text) > 15 else 16
        self.lbl_time.configure(text=text, font=("Helvetica", font_size, "bold"), text_color=color)

    def update_display(self, time_str, is_paused):
        self.lbl_time.configure(text=time_str, font=("Helvetica", 20, "bold"))

        if is_paused:
            self.lbl_time.configure(text_color="#e67e22")
            self.lbl_player.configure(text="PAUSIERT. Warte auf Klick...")
            # Button wird lediglich deaktiviert, da das Fortsetzen nur über DAW-Klick geschieht
            self.btn_pause.configure(state="disabled", text="||", fg_color=["#3a7ebf", "#1f538d"])
        else:
            self.lbl_time.configure(text_color="white")
            self.lbl_player.configure(text="Dein Zug")
            # Button ist bereit, um das Spiel zu pausieren
            self.btn_pause.configure(state="normal", text="||", fg_color=["#3a7ebf", "#1f538d"])