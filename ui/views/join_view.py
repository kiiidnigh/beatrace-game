import customtkinter as ctk
import tkinter.filedialog as filedialog
import os
from utils.file_utils import load_prefs, save_prefs
from config import settings


class JoinView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router

        self.prefs_file = os.path.join(settings.BASE_DIR, "host_prefs.json")
        self.prefs = load_prefs()
        self.selected_folder = self.prefs.get("last_join_folder", "")

        self.setup_ui()

    def setup_ui(self):
        # Header (Oben verankert)
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 0))

        btn_back = ctk.CTkButton(header_frame, text="◀ Zurück", width=80, height=35, font=("Helvetica", 14),
                                 fg_color="#636E72", hover_color="#2D3436", command=self.go_back)
        btn_back.pack(side="left")

        # Main Container (Zentriert den kompakten Formular-Block)
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        # Kompakter Formular-Block
        form_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        form_frame.pack(expand=True)

        ctk.CTkLabel(form_frame, text="Spiel beitreten", font=("Helvetica", 28, "bold")).pack(pady=(0, 30))

        ctk.CTkLabel(form_frame, text="Game Code (vom Host):", font=("Helvetica", 14)).pack(pady=5)
        self.code_entry = ctk.CTkEntry(form_frame, width=200, height=50, font=("Helvetica", 28, "bold"),
                                       justify="center")
        self.code_entry.pack(pady=(0, 20))

        # Drive Ordner Bereich
        frame_folder = ctk.CTkFrame(form_frame)
        frame_folder.pack(pady=10, fill="x")

        ctk.CTkLabel(frame_folder, text="Google Drive Basis-Ordner wählen:", font=("Helvetica", 14, "bold")).pack(
            pady=(15, 5))
        ctk.CTkLabel(frame_folder, text="(Der Ordner, in dem die Projekte synchronisiert werden)", text_color="gray",
                     font=("Helvetica", 12)).pack()

        ctk.CTkButton(frame_folder, text="Ordner auswählen", height=40, width=150, font=("Helvetica", 14),
                      command=self.choose_folder, fg_color="#636E72", hover_color="#2D3436").pack(pady=15)

        if self.selected_folder:
            initial_text = f"...{self.selected_folder[-35:]}"
            initial_color = "white"
        else:
            initial_text = "Nicht ausgewählt"
            initial_color = "gray"

        self.folder_label = ctk.CTkLabel(frame_folder, text=initial_text, text_color=initial_color,
                                         font=("Helvetica", 13))
        self.folder_label.pack(pady=(0, 15))

        # Join Button - Feste Höhe, damit er nicht zerquetscht wird!
        self.btn_join = ctk.CTkButton(form_frame, text="BEITRETEN", height=50, width=250,
                                      font=("Helvetica", 16, "bold"),
                                      fg_color="#1DB954", hover_color="#14833b", command=self.join_room)
        self.btn_join.pack(pady=(20, 5))

        self.error_label = ctk.CTkLabel(form_frame, text="", text_color="red", font=("Helvetica", 14))
        self.error_label.pack()

    def go_back(self):
        self.router.show_home()

    def choose_folder(self):
        initial_dir = self.selected_folder if self.selected_folder else os.path.expanduser("~")
        folder = filedialog.askdirectory(initialdir=initial_dir)

        if folder:
            self.selected_folder = folder
            self.folder_label.configure(text=f"...{folder[-35:]}", text_color="white")
            self.prefs["last_join_folder"] = self.selected_folder
            save_prefs(self.prefs)

    def join_room(self):
        code = self.code_entry.get().strip().upper()
        if not code or len(code) < 3:
            self.error_label.configure(text="Ungültiger Code!")
            return
        if not self.selected_folder:
            self.error_label.configure(text="Bitte Drive Ordner auswählen!")
            return

        self.game_state.room_code = code
        self.game_state.local_drive_folder = self.selected_folder

        self.router.show_lobby()