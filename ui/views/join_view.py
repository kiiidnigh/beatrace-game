# ================================================
# FILE: ui/views/join_view.py
# ================================================
import customtkinter as ctk
from core.i18n import translate
from ui.views.base_view import BaseView


class JoinView(BaseView):
    def __init__(self, master, game_state, network, router, **kwargs):
        super().__init__(master, **kwargs)
        self.game_state = game_state
        self.network = network
        self.router = router

        self._listeners = {
            "LANGUAGE_CHANGED": self.update_texts
        }
        self.register_listeners()

        self.setup_ui()

    def update_texts(self, data=None):
        self.btn_back.configure(text=translate("common.btn_back"))
        self.lbl_title.configure(text=translate("join.title"))
        self.lbl_code.configure(text=translate("join.code_label"))
        self.btn_join.configure(text=translate("join.btn_join"))
        self.error_label.configure(text="")

    def setup_ui(self):
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

        self.lbl_title = ctk.CTkLabel(form_frame, text=translate("join.title"), font=("Helvetica", 28, "bold"))
        self.lbl_title.pack(pady=(0, 40))

        self.lbl_code = ctk.CTkLabel(form_frame, text=translate("join.code_label"), font=("Helvetica", 14))
        self.lbl_code.pack(pady=5)

        self.code_entry = ctk.CTkEntry(form_frame, width=250, height=60, font=("Helvetica", 32, "bold"),
                                       justify="center")

        if self.game_state.room_code:
            self.code_entry.insert(0, self.game_state.room_code)

        self.code_entry.pack(pady=(0, 30))

        # KISS & DRY: Kein lokaler Ordner-Browser mehr nötig! Rclone lädt direkt in die AppData Sandbox.
        self.btn_join = ctk.CTkButton(form_frame, text=translate("join.btn_join"), height=55, width=250,
                                      font=("Helvetica", 16, "bold"),
                                      fg_color="#1DB954", hover_color="#14833b", command=self.join_room)
        self.btn_join.pack(pady=(10, 5))

        self.error_label = ctk.CTkLabel(form_frame, text="", text_color="red", font=("Helvetica", 14))
        self.error_label.pack()

    def join_room(self):
        code = self.code_entry.get().strip().upper()
        if not code or len(code) < 3:
            self.error_label.configure(text=translate("join.err_invalid_code"))
            return

        self.game_state.room_code = code
        self.router.show_lobby()