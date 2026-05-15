# ================================================
# FILE: ui/views/home_view.py
# ================================================
import customtkinter as ctk
from utils.file_utils import load_prefs, save_prefs
from core.i18n import translate
from ui.views.base_view import BaseView
from core.event_bus import EventBus


class HomeView(BaseView):
    def __init__(self, master, game_state, network, router, **kwargs):
        super().__init__(master, **kwargs)
        self.game_state = game_state
        self.router = router

        self.game_state.my_name = self.router.app_core.identity_service.get_display_name()
        self.game_state.reset_match_data()

        self._listeners = {
            "LANGUAGE_CHANGED": lambda d: self.safe_execute(self.update_texts)
        }
        self.register_listeners()

        self.setup_ui()

    def update_texts(self):
        self.btn_friends.configure(text=translate("home.btn_friends"))
        self.btn_settings.configure(text=translate("home.btn_settings"))
        self.lbl_title.configure(text=translate("home.title"))
        self.lbl_player_name.configure(text=translate("home.player_name_label"))
        self.btn_host.configure(text=translate("home.btn_host"))
        self.btn_join.configure(text=translate("home.btn_join"))
        self.lbl_my_id.configure(text=f"{translate('home.friend_code_badge')} {self.game_state.my_identity}")
        self.error_label.configure(text="")

    def setup_ui(self):
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=10)

        # Nutzt nun die zentrale Router-Funktion
        self.btn_friends = ctk.CTkButton(top_frame, text=translate("home.btn_friends"), width=120, height=35,
                                         font=("Helvetica", 14, "bold"),
                                         fg_color="#3a7ebf", hover_color="#1f538d", command=self.router.open_friends)
        self.btn_friends.pack(side="left")

        # Nutzt nun die zentrale Router-Funktion
        self.btn_settings = ctk.CTkButton(top_frame, text=translate("home.btn_settings"), width=120, height=35,
                                          font=("Helvetica", 14),
                                          fg_color="#636E72", hover_color="#2D3436", command=self.router.open_settings)
        self.btn_settings.pack(side="right")

        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(expand=True)

        self.lbl_title = ctk.CTkLabel(center_frame, text=translate("home.title"), font=("Helvetica", 50, "bold"),
                                      text_color="#1DB954")
        self.lbl_title.pack(pady=(0, 10))

        self.lbl_player_name = ctk.CTkLabel(center_frame, text=translate("home.player_name_label"),
                                            font=("Helvetica", 16))
        self.lbl_player_name.pack(pady=(0, 5))

        name_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        name_frame.pack(pady=10)

        self.name_entry = ctk.CTkEntry(name_frame, width=250, height=50, font=("Helvetica", 18), justify="center")
        if self.game_state.my_name:
            self.name_entry.insert(0, self.game_state.my_name)

        self.name_entry.configure(state="disabled", text_color="gray")
        self.name_entry.pack(side="left", padx=(0, 10))

        self._is_editing_name = False
        self.btn_edit_name = ctk.CTkButton(name_frame, text="✎", width=50, height=50, font=("Helvetica", 24),
                                           fg_color="#2D3436", hover_color="#636E72", command=self._toggle_edit_name)
        self.btn_edit_name.pack(side="left")

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

        self.identity_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.identity_frame.pack(side="bottom", pady=20)

        id_display = f"{translate('home.friend_code_badge')} {self.game_state.my_identity}"
        self.lbl_my_id = ctk.CTkLabel(self.identity_frame, text=id_display, font=("Courier", 12, "bold"),
                                      text_color="gray")
        self.lbl_my_id.pack(side="left", padx=10)

        self.btn_copy_id = ctk.CTkButton(
            self.identity_frame, text="📋", width=30, height=24,
            fg_color="#2D3436", hover_color="#636E72", command=self._copy_my_id
        )
        self.btn_copy_id.pack(side="left")

    def _toggle_edit_name(self):
        if not self._is_editing_name:
            self._is_editing_name = True
            self.name_entry.configure(state="normal", text_color="white")
            self.name_entry.focus()
            self.btn_edit_name.configure(text="✓", fg_color="#1DB954", hover_color="#14833b")
            self.name_entry.bind("<Return>", lambda e: self._toggle_edit_name())
        else:
            if self._save_username():
                self.error_label.configure(text="")
                self._is_editing_name = False
                self.name_entry.unbind("<Return>")
                self.name_entry.configure(state="disabled", text_color="gray")
                self.btn_edit_name.configure(text="✎", fg_color="#2D3436", hover_color="#636E72")
            else:
                self.error_label.configure(text="Name muss mind. 3 Zeichen lang sein!")

    def _copy_my_id(self):
        self.clipboard_clear()
        self.clipboard_append(self.game_state.my_identity)
        self.update()
        self.btn_copy_id.configure(text="✓", fg_color="#1DB954", hover_color="#14833b")
        self.after(2000, lambda: self.btn_copy_id.configure(text="📋", fg_color="#2D3436", hover_color="#636E72"))

    def _save_username(self):
        name = self.name_entry.get().strip()
        if len(name) >= 3:
            self.game_state.my_name = name

            prefs = load_prefs()
            prefs["last_username"] = name
            save_prefs(prefs)

            self.router.app_core.identity_service.set_display_name(name)

            EventBus.emit("CMD_BROADCAST_PRESENCE")
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