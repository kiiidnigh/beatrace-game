# ================================================
# FILE: ui/views/home_view.py
# ================================================
import customtkinter as ctk
from utils.file_utils import load_prefs, save_prefs
from ui.components.settings_modal import SettingsModal
from core.i18n import translate
from core.event_bus import EventBus


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

        # Auf On-The-Fly Sprachwechsel hören
        EventBus.subscribe("LANGUAGE_CHANGED", self._on_language_changed)

    def destroy(self):
        """Cleanup, um Event-Leaks bei View-Wechseln zu vermeiden."""
        EventBus.unsubscribe("LANGUAGE_CHANGED", self._on_language_changed)
        # Standard ctk Workaround
        self.pack_forget()
        self.after(100, lambda: ctk.CTkFrame.destroy(self))

    def _on_language_changed(self, data=None):
        """Wird aufgerufen, wenn in den Settings eine neue Sprache gespeichert wird."""
        self.after(0, self.update_texts)

    def update_texts(self):
        """Aktualisiert alle sichtbaren Texte dynamisch aus der Translator JSON."""
        self.btn_settings.configure(text=translate("home.btn_settings"))
        self.lbl_title.configure(text=translate("home.title"))
        self.lbl_player_name.configure(text=translate("home.player_name_label"))
        self.btn_host.configure(text=translate("home.btn_host"))
        self.btn_join.configure(text=translate("home.btn_join"))

        # Fehler-Text bei Sprachwechsel leeren, damit er nicht in der falschen Sprache hängen bleibt
        self.error_label.configure(text="")

    def setup_ui(self):
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(top_frame, text=translate("home.btn_settings"), width=120, height=35,
                                          font=("Helvetica", 14),
                                          fg_color="#636E72", hover_color="#2D3436", command=self.open_settings)
        self.btn_settings.pack(side="right")

        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(expand=True)

        self.lbl_title = ctk.CTkLabel(center_frame, text=translate("home.title"), font=("Helvetica", 50, "bold"),
                                      text_color="#1DB954")
        self.lbl_title.pack(pady=(0, 10))

        self.lbl_player_name = ctk.CTkLabel(center_frame, text=translate("home.player_name_label"), font=("Helvetica", 16))
        self.lbl_player_name.pack(pady=(0, 5))

        self.name_entry = ctk.CTkEntry(center_frame, width=300, height=50, font=("Helvetica", 18), justify="center")

        if self.game_state.my_name:
            self.name_entry.insert(0, self.game_state.my_name)
        self.name_entry.pack(pady=10)

        btn_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        btn_frame.pack(pady=40)

        self.btn_host = ctk.CTkButton(btn_frame, text=translate("home.btn_host"), height=55, width=200,
                                      font=("Helvetica", 14, "bold"),
                                      fg_color="#1DB954", hover_color="#14833b", command=self.go_host)
        self.btn_host.pack(side="left", padx=10)

        self.btn_join = ctk.CTkButton(btn_frame, text=translate("home.btn_join"), height=55, width=200,
                                      font=("Helvetica", 14, "bold"),
                                      fg_color="#636E72", hover_color="#2D3436", command=self.go_join)
        self.btn_join.pack(side="left", padx=10)

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
            self.error_label.configure(text=translate("home.error_no_name"))

    def go_join(self):
        if self._save_username():
            self.game_state.is_host = False
            self.router.show_join()
        else:
            self.error_label.configure(text=translate("home.error_no_name"))