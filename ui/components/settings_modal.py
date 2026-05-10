# ================================================
# FILE: ui/components/settings_modal.py
# ================================================
import customtkinter as ctk
from utils.file_utils import load_prefs, save_prefs
from utils.ui_utils import get_centered_geometry
from core.event_bus import EventBus
from core.i18n import translate, Translator


class SettingsModal(ctk.CTkToplevel):
    def __init__(self, master, on_save_callback=None):
        super().__init__(master)

        self.title(translate("settings.title"))
        self.attributes('-topmost', True)
        self.resizable(False, False)

        self.transient(master)
        self.grab_set()

        # Nutzt jetzt die saubere Helfer-Funktion aus den Utils
        self.geometry(get_centered_geometry(master, width=450, height=650))

        self.on_save_callback = on_save_callback
        self.prefs = load_prefs()
        if "sounds" not in self.prefs:
            self.prefs["sounds"] = {}

        self.lang_map = {"English": "en", "Deutsch": "de"}
        self.rev_lang_map = {"en": "English", "de": "Deutsch"}

        self.setup_ui()

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        self.tabview.add(translate("settings.tab_general"))
        self.tabview.add(translate("settings.tab_sound"))

        self._setup_general_tab()
        self._setup_sound_tab()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20, side="bottom")

        ctk.CTkButton(btn_frame, text=translate("common.btn_save"), fg_color="#1DB954", hover_color="#14833b",
                      command=self.save_and_close).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text=translate("common.btn_cancel"), fg_color="#c0392b", hover_color="#e74c3c",
                      command=self.destroy).pack(side="left", padx=10)

    def _setup_general_tab(self):
        tab = self.tabview.tab(translate("settings.tab_general"))

        lang_frame = ctk.CTkFrame(tab, fg_color="transparent")
        lang_frame.pack(fill="x", padx=10, pady=(10, 20))

        ctk.CTkLabel(lang_frame, text=translate("settings.language_label"), font=("Helvetica", 16, "bold")).pack(
            anchor="w")

        current_lang_code = self.prefs.get("language", "en")
        current_lang_name = self.rev_lang_map.get(current_lang_code, "English")

        self.lang_var = ctk.StringVar(value=current_lang_name)
        self.lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=["English", "Deutsch"],
            variable=self.lang_var,
            fg_color="#2D3436",
            button_color="#636E72"
        )
        self.lang_menu.pack(anchor="w", pady=(5, 0))

        ctk.CTkLabel(tab, text=translate("settings.ux_mode_label"), font=("Helvetica", 16, "bold")).pack(pady=(10, 10))

        self.mode_var = ctk.StringVar(value=self.prefs.get("ui_mode", "Standard"))

        modes = [
            ("Standard", translate("settings.ux_standard_desc")),
            ("Mini-Player", translate("settings.ux_mini_desc")),
            ("Stealth", translate("settings.ux_stealth_desc"))
        ]

        for mode, desc in modes:
            frame = ctk.CTkFrame(tab, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkRadioButton(frame, text=mode, variable=self.mode_var, value=mode,
                               font=("Helvetica", 14, "bold")).pack(anchor="w")
            ctk.CTkLabel(frame, text=desc, font=("Helvetica", 12), text_color="gray", justify="left").pack(anchor="w",
                                                                                                           padx=25)

    def _setup_sound_tab(self):
        tab = self.tabview.tab(translate("settings.tab_sound"))

        vol_frame = ctk.CTkFrame(tab)
        vol_frame.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkLabel(vol_frame, text=translate("settings.master_volume"), font=("Helvetica", 14, "bold")).pack(
            pady=(10, 5))
        self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=100, number_of_steps=100)
        self.vol_slider.set(self.prefs["sounds"].get("master_volume", 80))
        self.vol_slider.pack(fill="x", padx=20, pady=(0, 10))

        self.toggles = {}
        sound_options = [
            ("btn_click", translate("settings.snd_btn_click")),
            ("lobby_join", translate("settings.snd_lobby_join")),
            ("lobby_leave", translate("settings.snd_lobby_leave")),
            ("match_start", translate("settings.snd_match_start")),
            ("tick", translate("settings.snd_tick")),
            ("turn_end", translate("settings.snd_turn_end")),
            ("eliminated", translate("settings.snd_eliminated")),
            ("match_finish", translate("settings.snd_match_finish"))
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

        selected_lang_name = self.lang_var.get()
        new_lang_code = self.lang_map.get(selected_lang_name, "en")

        lang_changed = self.prefs.get("language") != new_lang_code
        self.prefs["language"] = new_lang_code

        self.prefs["sounds"]["master_volume"] = self.vol_slider.get()
        for key, var in self.toggles.items():
            self.prefs["sounds"][key] = var.get()

        save_prefs(self.prefs)
        EventBus.emit("SETTINGS_UPDATED")

        if lang_changed:
            Translator.initialize()
            EventBus.emit("LANGUAGE_CHANGED")

        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()