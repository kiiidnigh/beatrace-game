import customtkinter as ctk
import tkinter.filedialog as filedialog
import random
import string
import os
import re
from config import settings
from utils.file_utils import load_prefs, save_prefs, get_available_templates, open_template_folder


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

        btn_back = ctk.CTkButton(header_frame, text="◀ Zurück", width=80, height=35, font=("Helvetica", 14),
                                 fg_color="#636E72", hover_color="#2D3436", command=self.go_back)
        btn_back.pack(side="left")

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        form_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        form_frame.pack(expand=True)

        ctk.CTkLabel(form_frame, text="Spiel konfigurieren", font=("Helvetica", 28, "bold")).pack(pady=(0, 20))

        frame_template = ctk.CTkFrame(form_frame)
        frame_template.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(frame_template, text="FL Studio Start-Template:", font=("Helvetica", 14, "bold")).pack(
            pady=(10, 2), padx=15, anchor="w")

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

        btn_manage = ctk.CTkButton(
            temp_select_frame,
            text="📁 Verwalten",
            width=100,
            fg_color="transparent",
            border_width=1,
            command=open_template_folder
        )
        btn_manage.pack(side="left", padx=5)

        frame_time = ctk.CTkFrame(form_frame)
        frame_time.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(frame_time, text="Startzeit pro Spieler (Minuten):", font=("Helvetica", 14)).pack(pady=(10, 2))
        self.time_entry = ctk.CTkEntry(frame_time, font=("Helvetica", 14), justify="center", width=120)
        self.time_entry.insert(0, str(self.prefs.get("last_time", 15)))
        self.time_entry.pack(pady=(0, 10))

        frame_rules = ctk.CTkFrame(form_frame)
        frame_rules.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(frame_rules, text="Strafzeit für Spielpausierung (Sekunden):", font=("Helvetica", 14)).pack(
            pady=(10, 2))
        self.penalty_entry = ctk.CTkEntry(frame_rules, font=("Helvetica", 14), justify="center", width=120)
        self.penalty_entry.insert(0, str(self.prefs.get("last_penalty", 0)))
        self.penalty_entry.pack(pady=(0, 10))

        self.distribute_switch = ctk.CTkSwitch(frame_rules, text="Restzeit aufteilen, wenn Spieler aufgibt/fertig ist",
                                               font=("Helvetica", 13))
        self.distribute_switch.pack(pady=(0, 15))
        if self.prefs.get("last_distribute", True):
            self.distribute_switch.select()
        else:
            self.distribute_switch.deselect()

        frame_file = ctk.CTkFrame(form_frame)
        frame_file.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(frame_file, text="Match-Ordner Modus:", font=("Helvetica", 14, "bold")).pack(pady=(10, 5))

        self.mode_var = ctk.StringVar(value="Automatisch")
        self.seg_button = ctk.CTkSegmentedButton(
            frame_file,
            values=["Automatisch", "Manuell Wählen"],
            command=self.on_file_mode_change,
            variable=self.mode_var,
            font=("Helvetica", 13)
        )
        self.seg_button.pack(pady=5)

        self.file_label = ctk.CTkLabel(frame_file, text="Wird geladen...", text_color="gray", font=("Helvetica", 12))
        self.file_label.pack(pady=(0, 10))

        self.btn_create = ctk.CTkButton(form_frame, text="RAUM ERSTELLEN", height=50, width=250,
                                        font=("Helvetica", 16, "bold"),
                                        fg_color="#1DB954", hover_color="#14833b", command=self.create_room)
        self.btn_create.pack(pady=(20, 5))

        self.error_label = ctk.CTkLabel(form_frame, text="", text_color="red", font=("Helvetica", 14))
        self.error_label.pack()

        self.apply_auto_mode()

    def go_back(self):
        self.router.show_home()

    def on_file_mode_change(self, value):
        if value == "Manuell Wählen":
            self.choose_folder()
            self.mode_var.set("Automatisch")

        self.apply_auto_mode()

    def apply_auto_mode(self):
        if self.selected_base_folder and os.path.exists(self.selected_base_folder):
            auto_name = self.get_next_foldername(self.selected_base_folder)
            self.selected_match_dir = os.path.join(self.selected_base_folder, auto_name)
            self.update_file_label(is_auto=True)
        else:
            self.selected_match_dir = ""
            self.file_label.configure(
                text="Kein vorheriger Ordner gefunden.\nBitte wähle einmalig 'Manuell Wählen'.", text_color="orange")

    def update_file_label(self, is_auto=False):
        if self.selected_match_dir:
            base_name = os.path.basename(self.selected_base_folder)
            match_name = os.path.basename(self.selected_match_dir)
            auto_text = "\n(Ordner wird beim Start automatisch erstellt)" if is_auto else ""
            self.file_label.configure(text=f"Basis: .../{base_name}\nMatch-Ordner: {match_name}{auto_text}",
                                      text_color="#1DB954")

    def choose_folder(self):
        initial_dir = self.selected_base_folder if self.selected_base_folder else os.path.expanduser("~")

        path = filedialog.askdirectory(
            initialdir=initial_dir,
            title="Wähle deinen Cloud Basis-Ordner (z.B. Google Drive/BeatRace)"
        )
        if path:
            self.selected_base_folder = path
            self.prefs["last_folder"] = self.selected_base_folder
            save_prefs(self.prefs)
            return True
        return False

    def create_room(self):
        if not self.selected_match_dir:
            self.error_label.configure(text="Bitte wähle oder erstelle einen Match-Ordner!")
            return

        try:
            self.game_state.start_time_minutes = int(self.time_entry.get())
            self.game_state.penalty_seconds = int(self.penalty_entry.get())
        except ValueError:
            self.error_label.configure(text="Zeiten müssen Zahlen sein!")
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

        # FIX: Sauberes Setzen der Host-Zeiten über das neue Setter-System!
        self.game_state.set_player_time(self.game_state.my_name, self.game_state.start_time_minutes * 60)
        self.game_state.set_bonus_text(self.game_state.my_name, "")

        self.game_state.room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        self.router.show_lobby()