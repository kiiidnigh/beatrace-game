# ================================================
# FILE: ui/views/lobby_view.py
# ================================================
import customtkinter as ctk
import tkinter.messagebox as messagebox
import logging
from core.event_bus import EventBus
from core.i18n import translate


class LobbyView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router
        self.player_labels = {}

        self._is_destroyed = False

        self._listeners = {
            "NET_CONNECTED": lambda d: self.safe_execute(self._apply_connected),
            "NET_CLIENT_JOIN": lambda d: self.safe_execute(self._apply_client_join, d),
            "NET_NAME_TAKEN": lambda d: self.safe_execute(self._apply_name_taken, d),
            "NET_SYNC_STATE": lambda d: self.safe_execute(self._apply_sync_state, d),
            "NET_CLIENT_LEAVE": lambda d: self.safe_execute(self._apply_client_leave, d),
            "NET_LOBBY_CLOSED": lambda d: self.safe_execute(self._apply_lobby_closed),
            "NET_START_MATCH": lambda d: self.safe_execute(self.router.start_game),
            "LANGUAGE_CHANGED": lambda d: self.safe_execute(self.update_texts)
        }

        self.setup_ui()
        self._setup_event_listeners()

        self.network.connect(self.game_state.my_name, self.game_state.room_code)

        if self.game_state.is_host:
            self.game_state.ready_players.add(self.game_state.my_name)
            self.update_player_list()

    def update_texts(self):
        self.lbl_code_title.configure(text=translate("lobby.code_label"))
        self.lbl_players.configure(text=translate("lobby.players_label"))

        if self.game_state.is_host:
            self.btn_start.configure(text=translate("lobby.btn_start"))
            self.btn_close.configure(text=translate("lobby.btn_close"))
            self.update_settings_ui()
        else:
            self.lbl_wait.configure(text=translate("lobby.wait_for_host"))
            self.btn_leave.configure(text=translate("lobby.btn_leave"))

        self.update_player_list()

    def _setup_event_listeners(self):
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def destroy(self):
        self._is_destroyed = True
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

    def setup_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        center_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        center_frame.pack(expand=True)

        self.lbl_code_title = ctk.CTkLabel(center_frame, text=translate("lobby.code_label"), font=("Helvetica", 14, "bold"),
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
        self.lbl_settings = ctk.CTkLabel(self.settings_frame, text=translate("lobby.loading_settings"), text_color="gray",
                                         font=("Helvetica", 14))
        self.lbl_settings.pack(pady=10, padx=20)

        if self.game_state.is_host:
            self.update_settings_ui()

        list_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        list_container.pack(fill="x", pady=10)

        self.lbl_players = ctk.CTkLabel(list_container, text=translate("lobby.players_label"), font=("Helvetica", 16, "bold"))
        self.lbl_players.pack(anchor="w", pady=(0, 5))

        self.players_frame = ctk.CTkScrollableFrame(list_container, fg_color="#1e1e1e", width=450, height=180)
        self.players_frame.pack(fill="x")

        self.action_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=(30, 0))

        if self.game_state.is_host:
            btn_center = ctk.CTkFrame(self.action_frame, fg_color="transparent")
            btn_center.pack(expand=True)

            self.btn_start = ctk.CTkButton(btn_center, text=translate("lobby.btn_start"), height=50, width=220,
                                           font=("Helvetica", 16, "bold"),
                                           fg_color="#1DB954", hover_color="#14833b", command=self.host_start_game)
            self.btn_start.pack(side="left", padx=10)

            self.btn_close = ctk.CTkButton(btn_center, text=translate("lobby.btn_close"), height=50, width=220,
                                           font=("Helvetica", 16, "bold"),
                                           fg_color="#c0392b", hover_color="#e74c3c", command=self.close_lobby)
            self.btn_close.pack(side="left", padx=10)
        else:
            self.lbl_wait = ctk.CTkLabel(self.action_frame, text=translate("lobby.wait_for_host"),
                                         font=("Helvetica", 16, "bold"), text_color="orange")
            self.lbl_wait.pack(pady=(0, 15))

            self.btn_leave = ctk.CTkButton(self.action_frame, text=translate("lobby.btn_leave"), height=50, width=250,
                                           font=("Helvetica", 16, "bold"),
                                           fg_color="#c0392b", hover_color="#e74c3c", command=self.leave_lobby)
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

    def host_start_game(self):
        if len(self.game_state.players) < 2:
            self.btn_start.configure(text=translate("lobby.err_min_players"), fg_color="#c0392b", hover_color="#e74c3c")
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
        self.lbl_settings.configure(text=formatted, text_color="white")

    def update_player_list(self):
        for widget in self.players_frame.winfo_children():
            widget.destroy()

        for p in self.game_state.players:
            color = "#1DB954" if p in self.game_state.ready_players else "gray"
            host_tag = translate("lobby.host_suffix")
            display_text = f"• {p} {host_tag}" if p == self.game_state.players[0] else f"• {p}"
            ctk.CTkLabel(self.players_frame, text=display_text, font=("Helvetica", 18), text_color=color).pack(pady=5,
                                                                                                               anchor="w",
                                                                                                               padx=20)

    def _handle_name_taken(self):
        self.network.disconnect()
        messagebox.showerror(translate("common.error"), translate("lobby.err_name_taken"))
        self.router.show_home()

    def _handle_lobby_closed(self):
        self.network.disconnect()
        messagebox.showinfo(translate("lobby.closed_title"), translate("lobby.closed_msg"))
        self.router.show_home()

    def _apply_connected(self):
        if not self.game_state.is_host:
            self.network.send_signal("CLIENT_JOIN")

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
        data = payload.get("data", {})
        if not self.game_state.is_host:
            self.game_state.load_sync_data(data)
            self.game_state.ready_players = set(self.game_state.players)
            self.update_settings_ui()
            self.update_player_list()

    def _apply_client_leave(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            if sender in self.game_state.players: self.game_state.players.remove(sender)
            if sender in self.game_state.active_players: self.game_state.active_players.remove(sender)
            if sender in self.game_state.ready_players: self.game_state.ready_players.remove(sender)

            self.update_player_list()
            self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())

    def _apply_lobby_closed(self):
        if not self.game_state.is_host:
            self._handle_lobby_closed()