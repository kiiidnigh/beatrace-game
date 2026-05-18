# ================================================
# FILE: ui/components/settings_modal.py
# ================================================
import os
import threading
import tkinter.filedialog as filedialog
import customtkinter as ctk
from utils.file_utils import load_prefs, save_prefs
from utils.os_utils import extract_exe_icon
from utils.ui_utils import get_centered_geometry
from core.event_bus import EventBus
from core.events import UIEvents, SysEvents
from core.i18n import translate, Translator
from services.storage.rclone_adapter import RcloneCloudAdapter


class SettingsModal(ctk.CTkToplevel):
    def __init__(self, master, on_save_callback=None):
        super().__init__(master)

        self.title(translate("settings.title"))
        self.resizable(False, False)
        self.transient(master)

        self.geometry(get_centered_geometry(master, width=450, height=650))

        self.on_save_callback = on_save_callback
        self.prefs = load_prefs()
        if "sounds" not in self.prefs:
            self.prefs["sounds"] = {}

        self._temp_fl_path = self.prefs.get("fl_studio_path", "")

        self.lang_map = {"English": "en", "Deutsch": "de"}
        self.rev_lang_map = {"en": "English", "de": "Deutsch"}

        self.setup_ui()

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        self.tabview.add(translate("settings.tab_general"))
        self.tabview.add(translate("settings.tab_sound"))
        self.tabview.add(translate("settings.tab_daws"))

        # NEU: Cloud Sync Tab (SRP)
        self.tabview.add(translate("settings.tab_cloud"))

        self._setup_general_tab()
        self._setup_sound_tab()
        self._setup_daws_tab()
        self._setup_cloud_tab()

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
            ("lobby_join", translate("settings.snd_lobby_join", "Lobby Join")),
            ("lobby_leave", translate("settings.snd_lobby_leave", "Lobby Leave")),
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

    def _setup_daws_tab(self):
        tab = self.tabview.tab(translate("settings.tab_daws"))

        daw_frame = ctk.CTkFrame(tab, fg_color="#2D3436", corner_radius=8)
        daw_frame.pack(fill="x", padx=10, pady=(10, 15))

        header = ctk.CTkLabel(daw_frame, text="FL Studio", font=("Helvetica", 16, "bold"))
        header.pack(anchor="w", padx=15, pady=(10, 5))

        path_frame = ctk.CTkFrame(daw_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.lbl_daw_icon = ctk.CTkLabel(path_frame, text="🎹", font=("Helvetica", 24))
        self.lbl_daw_icon.pack(side="left", padx=(0, 10))

        self.lbl_daw_status = ctk.CTkLabel(path_frame, text="❌", font=("Helvetica", 18))
        self.lbl_daw_status.pack(side="left", padx=(0, 10))

        self.entry_daw_path = ctk.CTkEntry(path_frame, fg_color="#1e1e1e", text_color="gray", state="disabled")
        self.entry_daw_path.pack(side="left", padx=(0, 10), fill="x", expand=True)

        btn_browse = ctk.CTkButton(path_frame, text=translate("settings.btn_browse"), width=80,
                                   fg_color="#3a7ebf", hover_color="#1f538d", command=self._browse_fl_studio)
        btn_browse.pack(side="right")

        self._update_daw_status(self._temp_fl_path)

    def _setup_cloud_tab(self):
        """NEU: Rclone Authentifizierung UI (Fail Fast & KISS)"""
        tab = self.tabview.tab(translate("settings.tab_cloud"))
        self.cloud_adapter = RcloneCloudAdapter()

        ctk.CTkLabel(tab, text=translate("settings.cloud_status"), font=("Helvetica", 16, "bold")).pack(pady=(20, 5))

        self.lbl_cloud_status = ctk.CTkLabel(tab, text="", font=("Helvetica", 14))
        self.lbl_cloud_status.pack(pady=(0, 20))

        self.btn_auth = ctk.CTkButton(tab, text=translate("settings.btn_connect_cloud"),
                                      height=45, fg_color="#8e44ad", hover_color="#9b59b6",
                                      command=self._do_auth)
        self.btn_auth.pack(pady=10)

        self._update_cloud_status()

    def _update_cloud_status(self):
        if self.cloud_adapter.is_authenticated():
            self.lbl_cloud_status.configure(text=translate("settings.cloud_connected"), text_color="#1DB954")
            self.btn_auth.configure(state="disabled")
        else:
            self.lbl_cloud_status.configure(text=translate("settings.cloud_disconnected"), text_color="#c0392b")
            self.btn_auth.configure(state="normal", text=translate("settings.btn_connect_cloud"))

    def _do_auth(self):
        self.btn_auth.configure(state="disabled", text=translate("settings.auth_waiting"))

        def auth_task():
            try:
                self.cloud_adapter.authenticate()
                self.after(0, self._update_cloud_status)
                EventBus.emit(SysEvents.CLOUD_AUTH_SUCCESS)
            except Exception as e:
                self.after(0, self._update_cloud_status)
                EventBus.emit(SysEvents.CLOUD_AUTH_FAILED, {"error": str(e)})

        threading.Thread(target=auth_task, daemon=True).start()

    def _browse_fl_studio(self):
        initial = os.path.dirname(self._temp_fl_path) if os.path.exists(self._temp_fl_path) else "C:\\"
        path = filedialog.askopenfilename(
            title="FL Studio.exe auswählen",
            initialdir=initial,
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")]
        )
        if path:
            self._update_daw_status(path)

    def _update_daw_status(self, path):
        self._temp_fl_path = path

        self.entry_daw_path.configure(state="normal")
        self.entry_daw_path.delete(0, 'end')

        if path:
            self.entry_daw_path.insert(0, path)
        else:
            self.entry_daw_path.insert(0, translate("settings.status_missing"))

        self.entry_daw_path.configure(state="disabled")

        if path and os.path.exists(path) and path.lower().endswith(".exe"):
            self.lbl_daw_status.configure(text="✅", text_color="#1DB954")

            img = extract_exe_icon(path)
            if img:
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
                self.lbl_daw_icon.configure(image=ctk_img, text="")
            else:
                self.lbl_daw_icon.configure(image=None, text="🎹")
        else:
            self.lbl_daw_status.configure(text="❌", text_color="#c0392b")
            self.lbl_daw_icon.configure(image=None, text="🎹")

    def save_and_close(self):
        self.prefs["ui_mode"] = self.mode_var.get()
        self.prefs["fl_studio_path"] = self._temp_fl_path

        selected_lang_name = self.lang_var.get()
        new_lang_code = self.lang_map.get(selected_lang_name, "en")

        lang_changed = self.prefs.get("language") != new_lang_code
        self.prefs["language"] = new_lang_code

        self.prefs["sounds"]["master_volume"] = self.vol_slider.get()
        for key, var in self.toggles.items():
            self.prefs["sounds"][key] = var.get()

        save_prefs(self.prefs)
        EventBus.emit(UIEvents.SETTINGS_UPDATED)

        if lang_changed:
            Translator.initialize()
            EventBus.emit(UIEvents.LANGUAGE_CHANGED)

        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()