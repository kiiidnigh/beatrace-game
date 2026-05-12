# ================================================
# FILE: ui/views/lobby_view.py
# ================================================
import customtkinter as ctk
from utils.ui_utils import TextAnimator, CountdownTimer
from core.event_bus import EventBus
from core.i18n import translate
from ui.components.custom_popup import CustomPopup
from ui.components.invite_modal import InviteModal


class LobbyView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router
        self.player_labels = {}

        self._is_destroyed = False
        self._current_dots = ""

        self._join_state = "connecting" if not self.game_state.is_host else "synced"

        self.animator = TextAnimator(self)
        self.join_timer = None

        self._listeners = {
            "NET_CONNECTED": lambda d: self.safe_execute(self._apply_connected),
            "NET_CLIENT_JOIN": lambda d: self.safe_execute(self._apply_client_join, d),
            "NET_NAME_TAKEN": lambda d: self.safe_execute(self._apply_name_taken, d),
            "NET_SYNC_STATE": lambda d: self.safe_execute(self._apply_sync_state, d),
            "NET_CLIENT_LEAVE": lambda d: self.safe_execute(self._apply_client_leave, d),
            "NET_LOBBY_CLOSED": lambda d: self.safe_execute(self._apply_lobby_closed),
            "NET_START_MATCH": lambda d: self.safe_execute(self.router.start_game),
            "NET_FOLDER_VERIFIED": lambda d: self.safe_execute(self._apply_folder_verified, d),
            "SYS_WORKSPACE_READY": lambda d: self.safe_execute(self._on_workspace_ready, d),
            "SYS_HANDSHAKE_SUCCESS": lambda d: self.safe_execute(self._on_local_handshake_success),
            "SYS_HANDSHAKE_TIMEOUT": lambda d: self.safe_execute(self._on_handshake_timeout),
            "LANGUAGE_CHANGED": lambda d: self.safe_execute(self.update_texts)
        }

        self.setup_ui()

        self.animator.register(self._on_animate_tick)
        self.animator.start()

        self._setup_event_listeners()

        self.network.connect(self.game_state.my_name, self.game_state.room_code)

        if self.game_state.is_host:
            self.game_state.ready_players.add(self.game_state.my_name)
            self.game_state.verified_players.add(self.game_state.my_name)
            self.update_player_list()

    def update_texts(self):
        self.lbl_code_title.configure(text=translate("lobby.code_label"))
        self.lbl_players.configure(text=translate("lobby.players_label"))

        if self.game_state.is_host:
            self.btn_start.configure(text=translate("lobby.btn_start"))
            self.btn_invite.configure(text=translate("lobby.btn_invite"))
            self.btn_close.configure(text=translate("lobby.btn_close"))
            self.update_settings_ui()
        else:
            if self._join_state == "synced":
                self.lbl_wait.configure(text=translate("lobby.wait_for_host"))
                self.btn_leave.configure(text=translate("lobby.btn_leave"))

            if self.lbl_settings.cget("text_color") == "gray":
                self.lbl_settings.configure(text=translate("lobby.loading_settings").rstrip('.'))

        self.update_player_list()

    def _setup_event_listeners(self):
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def destroy(self):
        self._is_destroyed = True
        self.animator.stop()

        if self.join_timer:
            self.join_timer.stop()

        EventBus.emit("CMD_STOP_HANDSHAKE_CHECK")

        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)
        self.pack_forget()
        self.after(100, lambda: ctk.CTkFrame.destroy(self))

    def safe_execute(self, func, *args):
        def wrapper():
            if not self._is_destroyed and self.winfo_exists():
                try:
                    func(*args)
                except Exception:
                    pass

        self.after(0, wrapper)

    def _on_animate_tick(self, dots):
        self._current_dots = dots
        if self.lbl_settings.cget("text_color") == "gray":
            base = translate("lobby.loading_settings").rstrip('.')
            self.lbl_settings.configure(text=f"{base}{dots}")

        if getattr(self, "_join_state", "") == "connecting":
            self.lbl_wait.configure(text=f"Verbinde mit Broker{dots}")

        self.update_player_list()

    def setup_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        center_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        center_frame.pack(expand=True)

        self.lbl_code_title = ctk.CTkLabel(center_frame, text=translate("lobby.code_label"),
                                           font=("Helvetica", 14, "bold"),
                                           text_color="gray")
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

        self.lbl_settings = ctk.CTkLabel(
            self.settings_frame,
            text=translate("lobby.loading_settings").rstrip('.'),
            text_color="gray",
            font=("Helvetica", 14),
            width=250,
            anchor="w"
        )
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
                                           font=("Helvetica", 16, "bold"),
                                           fg_color="#1DB954", hover_color="#14833b", command=self.host_start_game)
            self.btn_start.pack(side="left", padx=5)

            # NEU: Der Einladen-Button in der Mitte!
            self.btn_invite = ctk.CTkButton(btn_center, text=translate("lobby.btn_invite"), height=50, width=140,
                                            font=("Helvetica", 16, "bold"),
                                            fg_color="#3a7ebf", hover_color="#1f538d", command=self.open_invite_modal)
            self.btn_invite.pack(side="left", padx=5)

            self.btn_close = ctk.CTkButton(btn_center, text=translate("lobby.btn_close"), height=50, width=170,
                                           font=("Helvetica", 16, "bold"),
                                           fg_color="#c0392b", hover_color="#e74c3c", command=self.close_lobby)
            self.btn_close.pack(side="left", padx=5)
        else:
            self.lbl_wait = ctk.CTkLabel(self.action_frame, text="Verbinde mit Broker...",
                                         font=("Helvetica", 16, "bold"), text_color="orange")
            self.lbl_wait.pack(pady=(0, 15))

            self.btn_leave = ctk.CTkButton(self.action_frame, text=translate("common.btn_cancel"), height=50, width=250,
                                           font=("Helvetica", 16, "bold"),
                                           fg_color="#c0392b", hover_color="#e74c3c", command=self._cancel_join)
            self.btn_leave.pack(expand=True)

    def open_invite_modal(self):
        InviteModal(self.winfo_toplevel(), self.game_state, self.network)

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
        if self.join_timer:
            self.join_timer.stop()
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

    def _on_workspace_ready(self, data):
        if self.game_state.is_host:
            self.game_state.workspace_id = data.get("workspace_id", "")

    def _on_local_handshake_success(self):
        self.game_state.verified_players.add(self.game_state.my_name)
        self.update_player_list()
        self.network.send_signal("FOLDER_VERIFIED")

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

    def _on_handshake_timeout(self):
        self.network.send_signal("CLIENT_LEAVE")
        self.network.disconnect()
        self.game_state.reset_match_data()

        def on_close(): self.router.show_join()

        CustomPopup(master=self.winfo_toplevel(), title=translate("common.error"),
                    message="Sync Timeout!\nDer ausgewählte Ordner passt nicht zum Host.",
                    icon="❌", btn_color="#c0392b", sound_type="error",
                    on_confirm_callback=on_close, on_cancel_callback=on_close)

    def _apply_folder_verified(self, payload):
        sender = payload.get("sender")
        if sender:
            self.game_state.verified_players.add(sender)
            self.update_player_list()

    def _handle_name_taken(self):
        self.network.disconnect()
        self.game_state.reset_match_data()

        def on_close(): self.router.show_home()

        CustomPopup(master=self.winfo_toplevel(), title=translate("common.error"),
                    message=translate("lobby.err_name_taken"), icon="❌", btn_color="#c0392b", sound_type="error",
                    on_confirm_callback=on_close, on_cancel_callback=on_close)

    def _handle_lobby_closed(self):
        self.network.disconnect()
        self.game_state.reset_match_data()

        def on_close(): self.router.show_home()

        CustomPopup(master=self.winfo_toplevel(), title=translate("lobby.closed_title"),
                    message=translate("lobby.closed_msg"), icon="ℹ️", btn_color="#3a7ebf", sound_type="info",
                    on_confirm_callback=on_close, on_cancel_callback=on_close)

    def _apply_connected(self):
        if not self.game_state.is_host:
            self.network.send_signal("CLIENT_JOIN")
            self._join_state = "waiting_host"
            self.join_timer = CountdownTimer(self, 12, self._on_join_tick, self._on_join_timeout)
            self.join_timer.start()

    def _apply_client_join(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            if sender in self.game_state.players:
                self.network.send_signal("NAME_TAKEN", data={"target": sender})
                return

            self.game_state.players.append(sender)
            self.game_state.active_players.append(sender)
            self.game_state.ready_players.add(sender)
            self.game_state.set_player_time(sender, self.game_state.start_time_minutes * 60)
            self.game_state.set_bonus_text(sender, "")

            self.update_player_list()
            self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())

    def _apply_name_taken(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host and data.get("target") == self.game_state.my_name:
            self._handle_name_taken()

    def _apply_sync_state(self, payload):
        if self.join_timer:
            self.join_timer.stop()

        data = payload.get("data", {})
        if not self.game_state.is_host:
            self._join_state = "synced"
            self.game_state.load_sync_data(data)
            self.game_state.ready_players = set(self.game_state.players)

            self.lbl_wait.configure(text=translate("lobby.wait_for_host"))
            self.btn_leave.configure(text=translate("lobby.btn_leave"), command=self.leave_lobby)

            self.update_settings_ui()
            self.update_player_list()

            EventBus.emit("CMD_VERIFY_WORKSPACE", data={
                "base_folder": self.game_state.local_drive_folder,
                "workspace_id": self.game_state.workspace_id
            })

    def _apply_client_leave(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            if sender in self.game_state.players: self.game_state.players.remove(sender)
            if sender in self.game_state.active_players: self.game_state.active_players.remove(sender)
            if sender in self.game_state.ready_players: self.game_state.ready_players.remove(sender)
            if sender in self.game_state.verified_players: self.game_state.verified_players.remove(sender)

            self.update_player_list()
            self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())

    def _apply_lobby_closed(self):
        if not self.game_state.is_host:
            self._handle_lobby_closed()