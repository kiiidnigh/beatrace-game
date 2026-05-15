# ================================================
# FILE: ui/views/setup_view.py
# ================================================
import customtkinter as ctk
from ui.views.base_view import BaseView


class SetupView(BaseView):
    def __init__(self, master, game_state, network, router, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.router = router
        self.game_state = game_state

        self.setup_ui()

    def setup_ui(self):
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(expand=True)

        ctk.CTkLabel(center_frame, text="Willkommen bei Beatrace!", font=("Helvetica", 36, "bold")).pack(pady=(0, 10))
        ctk.CTkLabel(center_frame, text="Bevor wir starten: Wie möchtest du im Spiel heißen?",
                     font=("Helvetica", 16), text_color="gray").pack(pady=(0, 30))

        self.entry_name = ctk.CTkEntry(center_frame, width=300, height=50, font=("Helvetica", 20),
                                       justify="center", placeholder_text="Dein Spielername")
        self.entry_name.pack(pady=10)
        self.entry_name.focus()

        self.lbl_error = ctk.CTkLabel(center_frame, text="", text_color="#c0392b", font=("Helvetica", 14))
        self.lbl_error.pack(pady=5)

        btn_save = ctk.CTkButton(center_frame, text="Profil erstellen", width=250, height=50,
                                 font=("Helvetica", 18, "bold"), fg_color="#1DB954", hover_color="#14833b",
                                 command=self.save_profile)
        btn_save.pack(pady=20)

        self.entry_name.bind("<Return>", lambda e: self.save_profile())

    def save_profile(self):
        name = self.entry_name.get().strip()

        if len(name) < 3:
            self.lbl_error.configure(text="Dein Name muss mindestens 3 Zeichen lang sein.")
            return

        # Nutze die injizierten Services
        self.router.app_core.identity_service.set_display_name(name)
        self.game_state.my_name = name
        self.router.app_core.identity_service.get_or_create_id()

        self.router.show_home()