# ================================================
# FILE: ui/views/host_view.py
# ================================================
import customtkinter as ctk
import random
import string
import os
from config import settings
from utils.file_utils import load_prefs, save_prefs, get_available_templates, open_template_folder
from core.i18n import translate
from ui.views.base_view import BaseView
from services.storage.rclone_adapter import RcloneCloudAdapter


class HostView(BaseView):
    def __init__(self, master, game_state, network, router, **kwargs):
        super().__init__(master, **kwargs)
        self.game_state = game_state
        self.network = network
        self.router = router

        self.prefs = load_prefs()
        self.cloud_adapter = RcloneCloudAdapter()
        self._is_cloud_ready = self.cloud_adapter.is_authenticated()

        self.template_data = get_available_templates()
        self.available_names = sorted(list(self.template_data.keys()))
        default_val = next((n for n in self.available_names if "default.flp" in n),
                           self.available_names[0] if self.available_names else "Keine Templates")

        self._listeners = {
            "LANGUAGE_CHANGED": self.update_texts
        }
        self.register_listeners()

        self.setup_ui(default_val)

    def update_texts(self):
        self.btn_back.configure(text=translate("common.btn_back"))
        self.lbl_title.configure(text=translate("host.title"))
        self.lbl_template.configure(text=translate("host.template_label"))
        self.btn_manage.configure(text=translate("host.btn_manage"))
        self.lbl_time.configure(text=translate("host.time_label"))
        self.lbl_penalty.configure(text=translate("host.penalty_label"))
        self.distribute_switch.configure(text=translate("host.distribute_label"))
        self.lbl_cloud.configure(text=translate("host.cloud_folder_label"))
        self.btn_create.configure(text=translate("host.btn_create"))

        if not self._is_cloud_ready:
            self.error_label.configure(text=translate("host.cloud_not_connected"))

    def setup_ui(self, default_val):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 0))

        self.btn_back = ctk.CTkButton(header_frame, text=translate("common.btn_back"), width=80, height=35,
                                      font=("Helvetica", 14),
                                      fg_color="#636E72", hover_color="#2D3436", command=self.router.show_home)
        self.btn_back.pack(side="left")

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        form_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        form_frame.pack(expand=True)

        self.lbl_title = ctk.CTkLabel(form_frame, text=translate("host.title"), font=("Helvetica", 28, "bold"))
        self.lbl_title.pack(pady=(0, 20))

        # --- Template ---
        frame_template = ctk.CTkFrame(form_frame)
        frame_template.pack(pady=5, padx=20, fill="x")

        self.lbl_template = ctk.CTkLabel(frame_template, text=translate("host.template_label"),
                                         font=("Helvetica", 14, "bold"))
        self.lbl_template.pack(pady=(10, 2), padx=15, anchor="w")

        temp_select_frame = ctk.CTkFrame(frame_template, fg_color="transparent")
        temp_select_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.template_var = ctk.StringVar(value=default_val)
        self.template_menu = ctk.CTkOptionMenu(
            temp_select_frame, values=self.available_names, variable=self.template_var,
            width=280, fg_color="#2D3436", button_color="#636E72"
        )
        self.template_menu.pack(side="left", padx=5)

        self.btn_manage = ctk.CTkButton(
            temp_select_frame, text=translate("host.btn_manage"), width=100,
            fg_color="transparent", border_width=1, command=open_template_folder
        )
        self.btn_manage.pack(side="left", padx=5)

        # --- Zeiten ---
        frame_time = ctk.CTkFrame(form_frame)
        frame_time.pack(pady=5, padx=20, fill="x")
        self.lbl_time = ctk.CTkLabel(frame_time, text=translate("host.time_label"), font=("Helvetica", 14))
        self.lbl_time.pack(pady=(10, 2))
        self.time_entry = ctk.CTkEntry(frame_time, font=("Helvetica", 14), justify="center", width=120)
        self.time_entry.insert(0, str(self.prefs.get("last_time", 15)))
        self.time_entry.pack(pady=(0, 10))

        # --- Regeln ---
        frame_rules = ctk.CTkFrame(form_frame)
        frame_rules.pack(pady=5, padx=20, fill="x")
        self.lbl_penalty = ctk.CTkLabel(frame_rules, text=translate("host.penalty_label"), font=("Helvetica", 14))
        self.lbl_penalty.pack(pady=(10, 2))
        self.penalty_entry = ctk.CTkEntry(frame_rules, font=("Helvetica", 14), justify="center", width=120)
        self.penalty_entry.insert(0, str(self.prefs.get("last_penalty", 0)))
        self.penalty_entry.pack(pady=(0, 10))

        self.distribute_switch = ctk.CTkSwitch(frame_rules, text=translate("host.distribute_label"),
                                               font=("Helvetica", 13))
        self.distribute_switch.pack(pady=(0, 15))
        if self.prefs.get("last_distribute", True):
            self.distribute_switch.select()
        else:
            self.distribute_switch.deselect()

        # --- NEU: Rclone Cloud Base Folder (KISS - Kein FileDialog mehr) ---
        frame_cloud = ctk.CTkFrame(form_frame)
        frame_cloud.pack(pady=5, padx=20, fill="x")

        self.lbl_cloud = ctk.CTkLabel(frame_cloud, text=translate("host.cloud_folder_label"),
                                      font=("Helvetica", 14, "bold"))
        self.lbl_cloud.pack(pady=(10, 5))

        self.cloud_entry = ctk.CTkEntry(frame_cloud, font=("Helvetica", 14), justify="center", width=250)
        self.cloud_entry.insert(0, self.prefs.get("last_cloud_folder", "Beatrace-Matches"))
        self.cloud_entry.pack(pady=(0, 15))

        # --- Aktion ---
        self.btn_create = ctk.CTkButton(form_frame, text=translate("host.btn_create"), height=50, width=250,
                                        font=("Helvetica", 16, "bold"),
                                        fg_color="#1DB954", hover_color="#14833b", command=self.create_room)
        self.btn_create.pack(pady=(20, 5))

        self.error_label = ctk.CTkLabel(form_frame, text="", text_color="red", font=("Helvetica", 14))
        self.error_label.pack()

        # Fail Fast: Wenn nicht in der Cloud eingeloggt, blockiere sofort!
        if not self._is_cloud_ready:
            self.btn_create.configure(state="disabled")
            self.error_label.configure(text=translate("host.cloud_not_connected"))

    def create_room(self):
        try:
            self.game_state.start_time_minutes = int(self.time_entry.get())
            self.game_state.penalty_seconds = int(self.penalty_entry.get())
        except ValueError:
            self.error_label.configure(text=translate("host.err_times_numeric"))
            return

        base_cloud_folder = self.cloud_entry.get().strip()
        if not base_cloud_folder:
            self.error_label.configure(text=translate("host.err_no_name"))
            return

        self.game_state.room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        # NEU: Der Pfad, der über das Netzwerk an alle Clients geht!
        self.game_state.cloud_remote_path = f"{base_cloud_folder}/Match_{self.game_state.room_code}/{self.game_state.project_filename}"

        display_name = self.template_var.get()
        self.game_state.selected_template_path = self.template_data.get(display_name, "")
        self.game_state.distribute_time = self.distribute_switch.get() == 1

        self.prefs["last_time"] = self.game_state.start_time_minutes
        self.prefs["last_penalty"] = self.game_state.penalty_seconds
        self.prefs["last_distribute"] = self.game_state.distribute_time
        self.prefs["last_cloud_folder"] = base_cloud_folder
        save_prefs(self.prefs)

        # DRY & SRP: HostView kümmert sich nicht mehr um das Workspace Setup.
        # Das macht der MatchManager beim Start der Runde automatisch!
        self.game_state.players = [self.game_state.my_name]
        self.game_state.active_players = [self.game_state.my_name]
        self.game_state.set_player_time(self.game_state.my_name, self.game_state.start_time_minutes * 60)
        self.game_state.set_bonus_text(self.game_state.my_name, "")

        self.game_state.verified_players.add(self.game_state.my_name)
        self.game_state.ready_players.add(self.game_state.my_name)

        self.router.show_lobby()