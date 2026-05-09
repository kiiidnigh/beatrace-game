# ================================================
# FILE: ui/components/settings_modal.py
# ================================================
import customtkinter as ctk
from utils.file_utils import load_prefs, save_prefs
from core.event_bus import EventBus


class SettingsModal(ctk.CTkToplevel):
    def __init__(self, master, on_save_callback=None):
        super().__init__(master)
        self.title("App Einstellungen")
        self.geometry("450x550")
        self.attributes('-topmost', True)
        self.resizable(False, False)

        self.on_save_callback = on_save_callback
        self.prefs = load_prefs()
        if "sounds" not in self.prefs:
            self.prefs["sounds"] = {}

        self.setup_ui()

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        self.tabview.add("Allgemein")
        self.tabview.add("Sound")

        self._setup_general_tab()
        self._setup_sound_tab()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20, side="bottom")

        ctk.CTkButton(btn_frame, text="Speichern", fg_color="#1DB954", hover_color="#14833b",
                      command=self.save_and_close).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Abbrechen", fg_color="#c0392b", hover_color="#e74c3c",
                      command=self.destroy).pack(side="left", padx=10)

    def _setup_general_tab(self):
        tab = self.tabview.tab("Allgemein")
        ctk.CTkLabel(tab, text="UX Modus (während deines Zuges)", font=("Helvetica", 16, "bold")).pack(pady=(20, 10))

        self.mode_var = ctk.StringVar(value=self.prefs.get("ui_mode", "Standard"))

        modes = [
            ("Standard", "Das normale Fenster bleibt offen."),
            ("Mini-Player", "Schwebendes, kleines Widget über FL Studio."),
            ("Stealth", "Fenster wird unsichtbar. Pause via STRG+SHIFT+P.")
        ]

        for mode, desc in modes:
            frame = ctk.CTkFrame(tab, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkRadioButton(frame, text=mode, variable=self.mode_var, value=mode,
                               font=("Helvetica", 14, "bold")).pack(anchor="w")
            ctk.CTkLabel(frame, text=desc, font=("Helvetica", 12), text_color="gray", justify="left").pack(anchor="w",
                                                                                                           padx=25)

    def _setup_sound_tab(self):
        tab = self.tabview.tab("Sound")

        # Master Volume
        vol_frame = ctk.CTkFrame(tab)
        vol_frame.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkLabel(vol_frame, text="Gesamtlautstärke:", font=("Helvetica", 14, "bold")).pack(pady=(10, 5))
        self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=100, number_of_steps=100)
        self.vol_slider.set(self.prefs["sounds"].get("master_volume", 80))
        self.vol_slider.pack(fill="x", padx=20, pady=(0, 10))

        # Sound Toggles
        self.toggles = {}
        sound_options = [
            ("btn_click", "Button Klick"),
            ("lobby_join", "Lobby Betreten"),
            ("lobby_leave", "Lobby Verlassen"),
            ("match_start", "Match Start"),
            ("tick", "Timer Tick (Letzte 10s)"),
            ("turn_end", "Zug Abgeben"),
            ("eliminated", "Spieler Ausgeschieden"),
            ("match_finish", "Match Ende")
        ]

        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        for key, label in sound_options:
            var = ctk.BooleanVar(value=self.prefs["sounds"].get(key, True))
            switch = ctk.CTkSwitch(scroll_frame, text=label, variable=var, font=("Helvetica", 13))
            switch.pack(anchor="w", pady=6)
            self.toggles[key] = var

    def save_and_close(self):
        self.prefs["ui_mode"] = self.mode_var.get()

        # Sounds speichern
        self.prefs["sounds"]["master_volume"] = self.vol_slider.get()
        for key, var in self.toggles.items():
            self.prefs["sounds"][key] = var.get()

        save_prefs(self.prefs)
        EventBus.emit("SETTINGS_UPDATED")  # SoundService informieren

        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()