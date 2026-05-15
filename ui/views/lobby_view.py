# ================================================
# FILE: ui/views/lobby_view.py
# ================================================
import customtkinter as ctk
from utils.ui_utils import TextAnimator, CountdownTimer
from core.event_bus import EventBus
from core.i18n import translate
from ui.components.custom_popup import CustomPopup
from ui.views.base_view import BaseView


class LobbyView(BaseView):
    def __init__(self, master, game_state, network, router, **kwargs):
        super().__init__(master, **kwargs)
        self.game_state = game_state
        self.network = network
        self.router = router
        self.player_labels = {}

        self._current_dots = ""
        self._ui_state = "connecting" if not self.game_state.is_host else "host"

        self.animator = TextAnimator(self)
        self.join_timer = None

        self._listeners = {
            "UI_LOBBY_REFRESH": self.update_texts,
            "UI_LOBBY_SYNCED": self._on_synced,
            "UI_LOBBY_ERROR_NAME_TAKEN": self._show_error_name_taken,
            "UI_LOBBY_ERROR_HANDSHAKE": self._show_error_handshake,
            "UI_LOBBY_HOST_CLOSED": self._show_lobby_closed,
            "NET_START_MATCH": self.router.start_game,
            "LANGUAGE_CHANGED": self.update_texts
        }
        self.register_listeners()

        self.setup_ui()
        self.animator.register(self._on_animate_tick)
        self.animator.start()

        if self.game_state.is_host:
            self.update_player_list()
        else:
            if not self.network.is_connected:
                self.join_timer = CountdownTimer(self, 12, self._on_join_tick, self._on_join_timeout)
                self.join_timer.start()
            else:
                self._on_synced()

    def update_texts(self):
        self.lbl_code_title.configure(text=translate("lobby.code_label"))
        self.lbl_players.configure(text=translate("lobby.players_label"))

        if self.game_state.is_host:
            self.btn_start.configure(text=translate("lobby.btn_start"))
            self.btn_invite.configure(text=translate("lobby.btn_invite"))
            self.btn_close.configure(text=translate("lobby.btn_close"))
            self.update_settings_ui()
        else:
            if self._ui_state == "synced":
                self.lbl_wait.configure(text=translate("lobby.wait_for_host"))
                self.btn_leave.configure(text=translate("lobby.btn_leave"))

            if self.lbl_settings.cget("text_color") == "gray":
                self.lbl_settings.configure(text=translate("lobby.loading_settings").rstrip('.'))

        self.update_player_list()

    def destroy(self):
        self.animator.stop()
        if self.join_timer:
            self.join_timer.stop()
        EventBus.emit("CMD_STOP_HANDSHAKE_CHECK")
        super().destroy()

    def _on_animate_tick(self, dots):
        self._current_dots = dots
        if self.lbl_settings.cget("text_color") == "gray":
            base = translate("lobby.loading_settings").rstrip('.')
            self.lbl_settings.configure(text=f"{base}{dots}")

        if self._ui_state == "connecting":
            self.lbl_wait.configure(text=f"Verbinde mit Broker{dots}")

        self.update_player_list()

    def setup_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        center_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        center_frame.pack(expand=True)

        self.lbl_code_title = ctk.CTkLabel(center_frame, text=translate("lobby.code_label"),
                                           font=("Helvetica", 14, "bold"), text_color="gray")
        self.lbl_code_title.pack(pady=(0, 5))

        code_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        code_frame.pack(pady=5)

        ctk.CTkLabel(code_frame, text=self.game_state.room_code, font=("Courier", 55, "bold"),
                     text_color="#1DB954").pack(side="left", padx=(0, 15))

        self.btn_copy = ctk.CTkButton(code_frame, text="📋", width=60, height=45, font=("Helvetica", 20),
                                      fg_color="#2D3436", hover_color="#636E72", command=self.copy_code)
        self.btn_copy.pack(side="left")

        self.settings_frame = ctk.CTkFrame(center_frame)
        self.settings_frame.pack(fill="x", pady=20)

        self.lbl_settings = ctk.CTkLabel(self.settings_frame, text=translate("lobby.loading_settings").rstrip('.'),
                                         text_color="gray", font=("Helvetica", 14), width=250, anchor="w")
        self.lbl_settings.pack(pady=10)

        if self.game_state.is_host:
            self.update_settings_ui()

        list_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        list_container.pack(fill="x", pady=10)

        self.lbl_players = ctk.CTkLabel(list_container, text=translate("lobby.players_label"),
                                        font=("Helvetica", 16, "bold"))
        self.lbl_players.pack(anchor="w", pady=(0, 5))

        self.players_frame = ctk.CTkScrollableFrame(list_container, fg_color="#1e1e1e", width=450, height=180)
        self.players_frame.pack(fill="x")

        self.action_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=(30, 0))

        if self.game_state.is_host:
            btn_center = ctk.CTkFrame(self.action_frame, fg_color="transparent")
            btn_center.pack(expand=True)

            self.btn_start = ctk.CTkButton(btn_center, text=translate("lobby.btn_start"), height=50, width=170,
                                           font=("Helvetica", 16, "bold"), fg_color="#1DB954", hover_color="#14833b",
                                           command=self.host_start_game)
            self.btn_start.pack(side="left", padx=5)

            # Nutzt nun die zentrale Router-Funktion
            self.btn_invite = ctk.CTkButton(btn_center, text=translate("lobby.btn_invite"), height=50, width=140,
                                            font=("Helvetica", 16, "bold"), fg_color="#3a7ebf", hover_color="#1f538d",
                                            command=self.router.open_invite)
            self.btn_invite.pack(side="left", padx=5)

            self.btn_close = ctk.CTkButton(btn_center, text=translate("lobby.btn_close"), height=50, width=170,
                                           font=("Helvetica", 16, "bold"), fg_color="#c0392b", hover_color="#e74c3c",
                                           command=self.close_lobby)
            self.btn_close.pack(side="left", padx=5)
        else:
            self.lbl_wait = ctk.CTkLabel(self.action_frame, text="Verbinde mit Broker...",
                                         font=("Helvetica", 16, "bold"), text_color="orange")
            self.lbl_wait.pack(pady=(0, 15))

            self.btn_leave = ctk.CTkButton(self.action_frame, text=translate("common.btn_cancel"), height=50, width=250,
                                           font=("Helvetica", 16, "bold"), fg_color="#c0392b", hover_color="#e74c3c",
                                           command=self._cancel_join)
            self.btn_leave.pack(expand=True)

    def copy_code(self):
        self.clipboard_clear()
        self.clipboard_append(self.game_state.room_code)
        self.update()
        self.btn_copy.configure(text="✔", fg_color="#1DB954", hover_color="#14833b")
        self.after(2000, lambda: self.btn_copy.configure(text="📋", fg_color="#2D3436", hover_color="#636E72"))

    def close_lobby(self):
        self.network.send_signal("LOBBY_CLOSED")
        self.network.disconnect()
        self.router.show_home()

    def leave_lobby(self):
        self.network.send_signal("CLIENT_LEAVE")
        self.network.disconnect()
        self.router.show_home()

    def _cancel_join(self):
        if self.join_timer: self.join_timer.stop()
        self.network.disconnect()
        self.game_state.reset_match_data()
        self.router.show_join()

    def host_start_game(self):
        if len(self.game_state.players) < 2:
            self.btn_start.configure(text=translate("lobby.err_min_players"), fg_color="#c0392b", hover_color="#e74c3c")
            self.after(2000, lambda: self.btn_start.configure(text=translate("lobby.btn_start"), fg_color="#1DB954",
                                                              hover_color="#14833b"))
            return

        if len(self.game_state.verified_players) < len(self.game_state.players):
            self.btn_start.configure(text="WAITING FOR SYNC...", fg_color="#e67e22", hover_color="#d35400")
            self.after(2000, lambda: self.btn_start.configure(text=translate("lobby.btn_start"), fg_color="#1DB954",
                                                              hover_color="#14833b"))
            return

        self.network.send_signal("START_MATCH")
        self.router.start_game()

    def update_settings_ui(self):
        dist = translate("common.yes") if self.game_state.distribute_time else translate("common.no")
        formatted = translate("lobby.settings_format").format(
            time=self.game_state.start_time_minutes,
            penalty=self.game_state.penalty_seconds,
            dist=dist,
            project=self.game_state.project_filename
        )
        self.lbl_settings.configure(text=formatted, text_color="white", width=0, anchor="center", justify="center")

    def update_player_list(self):
        current_players = self.game_state.players

        for p in list(self.player_labels.keys()):
            if p not in current_players:
                self.player_labels[p].destroy()
                del self.player_labels[p]

        for p in current_players:
            is_ready = p in self.game_state.ready_players
            is_verified = p in self.game_state.verified_players

            color = "#1DB954" if (is_ready and is_verified) else "gray"
            host_tag = translate("lobby.host_suffix") if p == self.game_state.players[0] else ""
            sync_tag = "" if is_verified else f"(Syncing{self._current_dots})"

            display_text = f"• {p} {host_tag} {sync_tag}".strip()

            if p not in self.player_labels:
                lbl = ctk.CTkLabel(self.players_frame, font=("Helvetica", 18))
                lbl.pack(pady=5, anchor="w", padx=20)
                self.player_labels[p] = lbl

            self.player_labels[p].configure(text=display_text, text_color=color)

    def _on_synced(self):
        if self.join_timer:
            self.join_timer.stop()
        self._ui_state = "synced"
        self.update_texts()

    def _on_join_tick(self, seconds_left):
        self.lbl_wait.configure(text=f"Suche Host... ({seconds_left}s)")

    def _on_join_timeout(self):
        self.network.disconnect()
        self.game_state.reset_match_data()

        def on_close(): self.router.show_join()

        CustomPopup(master=self.winfo_toplevel(), title=translate("common.error"),
                    message="Raum nicht gefunden!\nDer Code existiert nicht oder das Spiel wurde bereits beendet.",
                    icon="❌", btn_color="#c0392b", sound_type="error",
                    on_confirm_callback=on_close, on_cancel_callback=on_close)

    def _show_error_name_taken(self):
        def on_close(): self.router.show_home()

        CustomPopup(master=self.winfo_toplevel(), title=translate("common.error"),
                    message=translate("lobby.err_name_taken"), icon="❌", btn_color="#c0392b", sound_type="error",
                    on_confirm_callback=on_close, on_cancel_callback=on_close)

    def _show_error_handshake(self):
        def on_close(): self.router.show_join()

        CustomPopup(master=self.winfo_toplevel(), title=translate("common.error"),
                    message="Sync Timeout!\nDer ausgewählte Ordner passt nicht zum Host.",
                    icon="❌", btn_color="#c0392b", sound_type="error",
                    on_confirm_callback=on_close, on_cancel_callback=on_close)

    def _show_lobby_closed(self):
        def on_close(): self.router.show_home()

        CustomPopup(master=self.winfo_toplevel(), title=translate("lobby.closed_title"),
                    message=translate("lobby.closed_msg"), icon="ℹ️", btn_color="#3a7ebf", sound_type="info",
                    on_confirm_callback=on_close, on_cancel_callback=on_close)