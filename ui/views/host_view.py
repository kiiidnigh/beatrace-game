# ================================================
# FILE: ui/views/host_view.py
# ================================================
import customtkinter as ctk
import tkinter.filedialog as filedialog
import random
import string
import os
import re
from config import settings
from utils.file_utils import load_prefs, save_prefs, get_available_templates, open_template_folder
from core.i18n import translate
from core.event_bus import EventBus


class HostView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router

        self.prefs_file = os.path.join(settings.BASE_DIR, "host_prefs.json")
        self.prefs = load_prefs()

        self.selected_base_folder = self.prefs.get("last_folder", "")
        self.selected_match_dir = ""

        self.template_data = get_available_templates()
        self.available_names = sorted(list(self.template_data.keys()))

        default_val = next((n for n in self.available_names if "default.flp" in n),
                           self.available_names[0] if self.available_names else "Keine Templates")

        self.setup_ui(default_val)
        EventBus.subscribe("LANGUAGE_CHANGED", self._on_language_changed)

    def destroy(self):
        EventBus.unsubscribe("LANGUAGE_CHANGED", self._on_language_changed)
        self.pack_forget()
        self.after(100, lambda: ctk.CTkFrame.destroy(self))

    def _on_language_changed(self, data=None):
        self.after(0, self.update_texts)

    def update_texts(self):
        self.btn_back.configure(text=translate("common.btn_back"))
        self.lbl_title.configure(text=translate("host.title"))
        self.lbl_template.configure(text=translate("host.template_label"))
        self.btn_manage.configure(text=translate("host.btn_manage"))
        self.lbl_time.configure(text=translate("host.time_label"))
        self.lbl_penalty.configure(text=translate("host.penalty_label"))
        self.distribute_switch.configure(text=translate("host.distribute_label"))
        self.lbl_mode.configure(text=translate("host.folder_mode_label"))

        # Segmented Button Labels updaten
        new_values = [translate("host.mode_auto"), translate("host.mode_manual")]
        current_val = self.mode_var.get()
        mapped_val = new_values[0] if current_val in ["Automatisch", "Automatic"] else new_values[1]
        self.seg_button.configure(values=new_values)
        self.mode_var.set(mapped_val)

        self.btn_create.configure(text=translate("host.btn_create"))
        self.apply_auto_mode()
        self.error_label.configure(text="")

    def get_next_foldername(self, base_folder):
        max_num = 0
        try:
            for d in os.listdir(base_folder):
                if os.path.isdir(os.path.join(base_folder, d)):
                    match = re.match(r"Beatrace_Match_(\d+)", d)
                    if match:
                        max_num = max(max_num, int(match.group(1)))
        except:
            pass
        return f"Beatrace_Match_{max_num + 1}"

    def setup_ui(self, default_val):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 0))

        self.btn_back = ctk.CTkButton(header_frame, text=translate("common.btn_back"), width=80, height=35,
                                      font=("Helvetica", 14),
                                      fg_color="#636E72", hover_color="#2D3436", command=self.go_back)
        self.btn_back.pack(side="left")

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        form_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        form_frame.pack(expand=True)

        self.lbl_title = ctk.CTkLabel(form_frame, text=translate("host.title"), font=("Helvetica", 28, "bold"))
        self.lbl_title.pack(pady=(0, 20))

        frame_template = ctk.CTkFrame(form_frame)
        frame_template.pack(pady=5, padx=20, fill="x")

        self.lbl_template = ctk.CTkLabel(frame_template, text=translate("host.template_label"), font=("Helvetica", 14, "bold"))
        self.lbl_template.pack(pady=(10, 2), padx=15, anchor="w")

        temp_select_frame = ctk.CTkFrame(frame_template, fg_color="transparent")
        temp_select_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.template_var = ctk.StringVar(value=default_val)
        self.template_menu = ctk.CTkOptionMenu(
            temp_select_frame,
            values=self.available_names,
            variable=self.template_var,
            width=280,
            fg_color="#2D3436",
            button_color="#636E72"
        )
        self.template_menu.pack(side="left", padx=5)

        self.btn_manage = ctk.CTkButton(
            temp_select_frame,
            text=translate("host.btn_manage"),
            width=100,
            fg_color="transparent",
            border_width=1,
            command=open_template_folder
        )
        self.btn_manage.pack(side="left", padx=5)

        frame_time = ctk.CTkFrame(form_frame)
        frame_time.pack(pady=5, padx=20, fill="x")
        self.lbl_time = ctk.CTkLabel(frame_time, text=translate("host.time_label"), font=("Helvetica", 14))
        self.lbl_time.pack(pady=(10, 2))
        self.time_entry = ctk.CTkEntry(frame_time, font=("Helvetica", 14), justify="center", width=120)
        self.time_entry.insert(0, str(self.prefs.get("last_time", 15)))
        self.time_entry.pack(pady=(0, 10))

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

        frame_file = ctk.CTkFrame(form_frame)
        frame_file.pack(pady=5, padx=20, fill="x")
        self.lbl_mode = ctk.CTkLabel(frame_file, text=translate("host.folder_mode_label"), font=("Helvetica", 14, "bold"))
        self.lbl_mode.pack(pady=(10, 5))

        self.mode_var = ctk.StringVar(value=translate("host.mode_auto"))
        self.seg_button = ctk.CTkSegmentedButton(
            frame_file,
            values=[translate("host.mode_auto"), translate("host.mode_manual")],
            command=self.on_file_mode_change,
            variable=self.mode_var,
            font=("Helvetica", 13)
        )
        self.seg_button.pack(pady=5)

        self.file_label = ctk.CTkLabel(frame_file, text=translate("host.loading"), text_color="gray", font=("Helvetica", 12))
        self.file_label.pack(pady=(0, 10))

        self.btn_create = ctk.CTkButton(form_frame, text=translate("host.btn_create"), height=50, width=250,
                                        font=("Helvetica", 16, "bold"),
                                        fg_color="#1DB954", hover_color="#14833b", command=self.create_room)
        self.btn_create.pack(pady=(20, 5))

        self.error_label = ctk.CTkLabel(form_frame, text="", text_color="red", font=("Helvetica", 14))
        self.error_label.pack()

        self.apply_auto_mode()

    def go_back(self):
        self.router.show_home()

    def on_file_mode_change(self, value):
        if value == translate("host.mode_manual"):
            self.choose_folder()
            self.mode_var.set(translate("host.mode_auto"))
        self.apply_auto_mode()

    def apply_auto_mode(self):
        if self.selected_base_folder and os.path.exists(self.selected_base_folder):
            auto_name = self.get_next_foldername(self.selected_base_folder)
            self.selected_match_dir = os.path.join(self.selected_base_folder, auto_name)
            self.update_file_label(is_auto=True)
        else:
            self.selected_match_dir = ""
            self.file_label.configure(
                text=translate("host.no_folder_warning"), text_color="orange")

    def update_file_label(self, is_auto=False):
        if self.selected_match_dir:
            base_name = os.path.basename(self.selected_base_folder)
            match_name = os.path.basename(self.selected_match_dir)
            auto_text = translate("host.auto_folder_suffix") if is_auto else ""

            line1 = translate("host.base_folder_prefix").format(base_name)
            line2 = translate("host.match_folder_prefix").format(match_name)

            self.file_label.configure(text=f"{line1}\n{line2}{auto_text}", text_color="#1DB954")

    def choose_folder(self):
        initial_dir = self.selected_base_folder if self.selected_base_folder else os.path.expanduser("~")

        path = filedialog.askdirectory(
            initialdir=initial_dir,
            title=translate("host.dialog_choose_folder")
        )
        if path:
            self.selected_base_folder = path
            self.prefs["last_folder"] = self.selected_base_folder
            save_prefs(self.prefs)
            return True
        return False

    def create_room(self):
        if not self.selected_match_dir:
            self.error_label.configure(text=translate("host.err_no_folder"))
            return

        try:
            self.game_state.start_time_minutes = int(self.time_entry.get())
            self.game_state.penalty_seconds = int(self.penalty_entry.get())
        except ValueError:
            self.error_label.configure(text=translate("host.err_times_numeric"))
            return

        display_name = self.template_var.get()
        self.game_state.selected_template_path = self.template_data.get(display_name, "")
        self.game_state.distribute_time = self.distribute_switch.get() == 1

        self.prefs["last_time"] = self.game_state.start_time_minutes
        self.prefs["last_penalty"] = self.game_state.penalty_seconds
        self.prefs["last_distribute"] = self.game_state.distribute_time
        save_prefs(self.prefs)

        os.makedirs(self.selected_match_dir, exist_ok=True)
        self.game_state.match_folder_name = os.path.basename(self.selected_match_dir)
        self.game_state.local_drive_folder = self.selected_base_folder
        self.game_state.project_filename = "project.zip"

        self.game_state.players = [self.game_state.my_name]
        self.game_state.active_players = [self.game_state.my_name]

        self.game_state.set_player_time(self.game_state.my_name, self.game_state.start_time_minutes * 60)
        self.game_state.set_bonus_text(self.game_state.my_name, "")

        self.game_state.room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        self.router.show_lobby()