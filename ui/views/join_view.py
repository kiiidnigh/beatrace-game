# ================================================
# FILE: ui/views/join_view.py
# ================================================
import customtkinter as ctk
import tkinter.filedialog as filedialog
import os
from utils.file_utils import load_prefs, save_prefs
from config import settings
from core.i18n import translate
from ui.views.base_view import BaseView


class JoinView(BaseView):
    def __init__(self, master, game_state, network, router, **kwargs):
        super().__init__(master, **kwargs)
        self.game_state = game_state
        self.network = network
        self.router = router

        self.prefs_file = os.path.join(settings.BASE_DIR, "settings.json")
        self.prefs = load_prefs()
        self.selected_folder = self.prefs.get("last_join_folder", "")

        self._listeners = {
            "LANGUAGE_CHANGED": lambda d: self.safe_execute(self.update_texts)
        }
        self.register_listeners()

        self.setup_ui()

    def update_texts(self):
        self.btn_back.configure(text=translate("common.btn_back"))
        self.lbl_title.configure(text=translate("join.title"))
        self.lbl_code.configure(text=translate("join.code_label"))
        self.lbl_folder.configure(text=translate("join.folder_label"))
        self.lbl_folder_sub.configure(text=translate("join.folder_sub_label"))
        self.btn_choose.configure(text=translate("join.btn_choose_folder"))
        self.btn_join.configure(text=translate("join.btn_join"))
        self.error_label.configure(text="")

        if not self.selected_folder:
            self.folder_label.configure(text=translate("join.not_selected"))

    def setup_ui(self):
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

        self.lbl_title = ctk.CTkLabel(form_frame, text=translate("join.title"), font=("Helvetica", 28, "bold"))
        self.lbl_title.pack(pady=(0, 30))

        self.lbl_code = ctk.CTkLabel(form_frame, text=translate("join.code_label"), font=("Helvetica", 14))
        self.lbl_code.pack(pady=5)

        self.code_entry = ctk.CTkEntry(form_frame, width=200, height=50, font=("Helvetica", 28, "bold"),
                                       justify="center")

        if self.game_state.room_code:
            self.code_entry.insert(0, self.game_state.room_code)

        self.code_entry.pack(pady=(0, 20))

        frame_folder = ctk.CTkFrame(form_frame)
        frame_folder.pack(pady=10, fill="x")

        self.lbl_folder = ctk.CTkLabel(frame_folder, text=translate("join.folder_label"),
                                       font=("Helvetica", 14, "bold"))
        self.lbl_folder.pack(pady=(15, 5))

        self.lbl_folder_sub = ctk.CTkLabel(frame_folder, text=translate("join.folder_sub_label"), text_color="gray",
                                           font=("Helvetica", 12))
        self.lbl_folder_sub.pack()

        self.btn_choose = ctk.CTkButton(frame_folder, text=translate("join.btn_choose_folder"), height=40, width=150,
                                        font=("Helvetica", 14),
                                        command=self.choose_folder, fg_color="#636E72", hover_color="#2D3436")
        self.btn_choose.pack(pady=15)

        if self.selected_folder:
            initial_text = f"...{self.selected_folder[-35:]}"
            initial_color = "white"
        else:
            initial_text = translate("join.not_selected")
            initial_color = "gray"

        self.folder_label = ctk.CTkLabel(frame_folder, text=initial_text, text_color=initial_color,
                                         font=("Helvetica", 13))
        self.folder_label.pack(pady=(0, 15))

        self.btn_join = ctk.CTkButton(form_frame, text=translate("join.btn_join"), height=50, width=250,
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
            self.error_label.configure(text=translate("join.err_invalid_code"))
            return
        if not self.selected_folder:
            self.error_label.configure(text=translate("join.err_no_folder"))
            return

        self.game_state.room_code = code
        self.game_state.local_drive_folder = self.selected_folder

        self.router.show_lobby()