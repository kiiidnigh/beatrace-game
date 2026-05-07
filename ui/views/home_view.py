import customtkinter as ctk
from utils.file_utils import load_prefs, save_prefs
from ui.components.settings_modal import SettingsModal


class HomeView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.router = router

        # Einstellungen laden und Nutzernamen wiederherstellen
        prefs = load_prefs()
        self.game_state.my_name = prefs.get("last_username", "")

        # FIX: Sicheres Zurücksetzen aller Match-Daten über den Manager
        self.game_state.reset_match_data()

        self.setup_ui()

    def setup_ui(self):
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=10)

        btn_settings = ctk.CTkButton(top_frame, text="⚙️ Einstellungen", width=120, height=35, font=("Helvetica", 14),
                                     fg_color="#636E72", hover_color="#2D3436", command=self.open_settings)
        btn_settings.pack(side="right")

        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(expand=True)

        ctk.CTkLabel(center_frame, text="BEATRACE", font=("Helvetica", 50, "bold"), text_color="#1DB954").pack(
            pady=(0, 10))

        ctk.CTkLabel(center_frame, text="Dein Spielername:", font=("Helvetica", 16)).pack(pady=(0, 5))
        self.name_entry = ctk.CTkEntry(center_frame, width=300, height=50, font=("Helvetica", 18), justify="center")

        if self.game_state.my_name:
            self.name_entry.insert(0, self.game_state.my_name)
        self.name_entry.pack(pady=10)

        btn_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        btn_frame.pack(pady=40)

        ctk.CTkButton(btn_frame, text="SPIEL ERSTELLEN", height=55, width=200, font=("Helvetica", 14, "bold"),
                      fg_color="#1DB954", hover_color="#14833b", command=self.go_host).pack(side="left", padx=10)

        ctk.CTkButton(btn_frame, text="SPIEL BEITRETEN", height=55, width=200, font=("Helvetica", 14, "bold"),
                      fg_color="#636E72", hover_color="#2D3436", command=self.go_join).pack(side="left", padx=10)

        self.error_label = ctk.CTkLabel(center_frame, text="", text_color="red", font=("Helvetica", 14))
        self.error_label.pack()

    def open_settings(self):
        SettingsModal(self.winfo_toplevel())

    def _save_username(self):
        name = self.name_entry.get().strip()
        if name:
            self.game_state.my_name = name
            prefs = load_prefs()
            prefs["last_username"] = name
            save_prefs(prefs)
            return True
        return False

    def go_host(self):
        if self._save_username():
            self.game_state.is_host = True
            self.router.show_host()
        else:
            self.error_label.configure(text="Bitte gib einen Namen ein!")

    def go_join(self):
        if self._save_username():
            self.game_state.is_host = False
            self.router.show_join()
        else:
            self.error_label.configure(text="Bitte gib einen Namen ein!")