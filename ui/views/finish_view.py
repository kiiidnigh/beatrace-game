# ================================================
# FILE: ui/views/finish_view.py
# ================================================
import customtkinter as ctk
import os
import subprocess
from core.i18n import translate
from core.event_bus import EventBus
from ui.components.custom_popup import CustomPopup


class FinishView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router
        self.match_stats = self.game_state.match_stats

        self._is_destroyed = False
        self._lobby_closed_by_host = False  # NEU: Merkt sich, ob die Lobby im Hintergrund geschlossen wurde

        self.setup_ui()
        EventBus.subscribe("LANGUAGE_CHANGED", self._on_language_changed)
        EventBus.subscribe("NET_LOBBY_CLOSED", self._on_host_closed_lobby)

    def destroy(self):
        self._is_destroyed = True
        EventBus.unsubscribe("LANGUAGE_CHANGED", self._on_language_changed)
        EventBus.unsubscribe("NET_LOBBY_CLOSED", self._on_host_closed_lobby)
        self.pack_forget()
        self.after(100, lambda: ctk.CTkFrame.destroy(self))

    def _on_language_changed(self, data=None):
        if not self._is_destroyed and self.winfo_exists():
            self.update_texts()

    def update_texts(self):
        self.lbl_title.configure(text=translate("finish.title"))
        self.lbl_subtitle.configure(text=translate("finish.subtitle"))
        self.lbl_proj_data.configure(text=translate("finish.project_data_title"))
        self.lbl_awards.configure(text=translate("finish.awards_title"))
        self.btn_open.configure(text=translate("finish.btn_open_project"))
        self.btn_home.configure(text=translate("finish.btn_home"))

    def setup_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        header_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        self.lbl_title = ctk.CTkLabel(header_frame, text=translate("finish.title"), font=("Helvetica", 42, "bold"),
                                      text_color="#1DB954")
        self.lbl_title.pack()
        self.lbl_subtitle = ctk.CTkLabel(header_frame, text=translate("finish.subtitle"), font=("Helvetica", 16),
                                         text_color="gray")
        self.lbl_subtitle.pack()

        content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)

        left_panel = ctk.CTkScrollableFrame(content_frame, fg_color="#1e1e1e", width=400, corner_radius=10)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.lbl_proj_data = ctk.CTkLabel(left_panel, text=translate("finish.project_data_title"),
                                          font=("Helvetica", 20, "bold"))
        self.lbl_proj_data.pack(pady=(15, 15))

        project_data = self.match_stats.get("project_data", {})
        self._create_stat_row(left_panel, translate("finish.stat_file_size"),
                              self.match_stats.get("file_size", "0.00 MB"))

        if not project_data:
            ctk.CTkLabel(left_panel, text=translate("finish.no_data"), text_color="gray").pack(pady=20)
        else:
            for title, value in project_data.items():
                self._create_stat_row(left_panel, title, value)

        v_text = translate("finish.fl_version_prefix").format(self.match_stats.get('fl_version',
                                                                                   translate("common.unknown")))
        ctk.CTkLabel(left_panel, text=v_text, font=("Helvetica", 12), text_color="gray").pack(pady=(20, 10))

        right_panel = ctk.CTkScrollableFrame(content_frame, fg_color="#2D3436", width=400, corner_radius=10)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self.lbl_awards = ctk.CTkLabel(right_panel, text=translate("finish.awards_title"),
                                       font=("Helvetica", 20, "bold"), text_color="#f1c40f")
        self.lbl_awards.pack(pady=(15, 15))

        awards = self.match_stats.get("awards", {})
        if not awards:
            ctk.CTkLabel(right_panel, text=translate("finish.no_awards"), font=("Helvetica", 14),
                         text_color="gray").pack(expand=True, pady=50)
        else:
            for title, winner in awards.items():
                award_card = ctk.CTkFrame(right_panel, fg_color="#1e1e1e", corner_radius=8)
                award_card.pack(fill="x", padx=15, pady=8)

                ctk.CTkLabel(award_card, text=title, font=("Helvetica", 16, "bold"), text_color="#1DB954").pack(
                    anchor="w", padx=15, pady=(10, 0))
                ctk.CTkLabel(award_card, text=winner, font=("Helvetica", 14), text_color="white").pack(anchor="w",
                                                                                                       padx=15,
                                                                                                       pady=(0, 10))

        btn_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        btn_frame.pack(pady=(20, 0))

        self.btn_open = ctk.CTkButton(btn_frame, text=translate("finish.btn_open_project"), height=50, width=250,
                                      font=("Helvetica", 14, "bold"),
                                      fg_color="#8e44ad", hover_color="#9b59b6", command=self.open_project_folder)
        self.btn_open.pack(side="left", padx=10)

        self.btn_lobby = ctk.CTkButton(btn_frame, text="ZURÜCK ZUR LOBBY", height=50, width=250,
                                       font=("Helvetica", 14, "bold"),
                                       fg_color="#3a7ebf", hover_color="#1f538d", command=self.return_to_lobby)
        self.btn_lobby.pack(side="left", padx=10)

    def _on_host_closed_lobby(self, data=None):
        """Wird getriggert, wenn der Host die Lobby schließt. Wir merken uns das nur heimlich."""

        def handle_close():
            if self._is_destroyed or not self.winfo_exists():
                return
            # Statt den Spieler sofort rauszuwerfen, merken wir uns nur, dass die Lobby zu ist.
            self._lobby_closed_by_host = True

        self.after(0, handle_close)

    def _create_stat_row(self, parent, title, value):
        box = ctk.CTkFrame(parent, fg_color="#2D3436", corner_radius=8, height=60)
        box.pack(fill="x", padx=15, pady=6)
        box.pack_propagate(False)

        ctk.CTkLabel(box, text=title, font=("Helvetica", 14), text_color="gray").pack(side="left", padx=15)
        ctk.CTkLabel(box, text=str(value), font=("Helvetica", 16, "bold"), text_color="white").pack(side="right",
                                                                                                    padx=15)

    def open_project_folder(self):
        path = self.game_state.local_project_path
        if os.path.exists(path):
            subprocess.Popen(r'explorer /select,"{}"'.format(os.path.abspath(path)))
        else:
            folder = self.game_state.local_drive_folder
            if os.path.exists(folder):
                os.startfile(folder)

    def return_to_lobby(self):
        """Wird aufgerufen, wenn der Nutzer fertig ist und auf 'Zurück zur Lobby' klickt."""
        # Prüfen, ob der Host in der Zwischenzeit die Lobby geschlossen hat
        if self._lobby_closed_by_host:
            # Verbindung trennen und Daten bereinigen
            self.network.disconnect()
            self.game_state.reset_match_data()

            # Popup anzeigen und danach ins Hauptmenü schicken
            def on_close():
                self.router.show_home()

            CustomPopup(
                master=self.winfo_toplevel(),
                title=translate("lobby.closed_title"),
                message=translate("lobby.closed_msg"),
                icon="ℹ️",
                btn_color="#3a7ebf",
                sound_type="info",
                on_confirm_callback=on_close,
                on_cancel_callback=on_close
            )
        else:
            # Normale Rückkehr in die Lobby (Host ist noch da)
            EventBus.emit("CMD_RETURN_TO_LOBBY")