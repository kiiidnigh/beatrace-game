import customtkinter as ctk
import tkinter.messagebox as messagebox
import logging
from core.event_bus import EventBus


class LobbyView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router
        self.player_labels = {}

        # 1. WICHTIG: Alte Geister-Verbindungen kappen, bevor wir neu starten!
        EventBus.clear_all()

        self.setup_ui()
        self._setup_event_listeners()

        # 2. Netzwerkverbindung aufbauen
        self.network.connect(self.game_state.my_name, self.game_state.room_code)

        if self.game_state.is_host:
            self.game_state.ready_players.add(self.game_state.my_name)
            self.update_player_list()

    def _setup_event_listeners(self):
        EventBus.subscribe("NET_CONNECTED", lambda d: self.safe_execute(self._on_connected))
        EventBus.subscribe("NET_CLIENT_JOIN", lambda d: self.safe_execute(self._on_client_join, d))
        EventBus.subscribe("NET_NAME_TAKEN", lambda d: self.safe_execute(self._on_name_taken, d))
        EventBus.subscribe("NET_SYNC_STATE", lambda d: self.safe_execute(self._on_sync_state, d))
        EventBus.subscribe("NET_CLIENT_LEAVE", lambda d: self.safe_execute(self._on_client_leave, d))
        EventBus.subscribe("NET_LOBBY_CLOSED", lambda d: self.safe_execute(self._on_lobby_closed))
        EventBus.subscribe("NET_START_MATCH", lambda d: self.safe_execute(self.router.start_game))

    def safe_execute(self, func, *args):
        if self.winfo_exists():
            self.after(0, lambda: func(*args))

    def setup_ui(self):
        # 1. Main Container (Nimmt den ganzen Platz ein)
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        # 2. Kompakter Center Block (Wird zentriert)
        center_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        center_frame.pack(expand=True)

        # --- HEADER BEREICH ---
        ctk.CTkLabel(center_frame, text="LOBBY CODE", font=("Helvetica", 14, "bold"), text_color="gray").pack(
            pady=(0, 5))

        code_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        code_frame.pack(pady=5)

        ctk.CTkLabel(code_frame, text=self.game_state.room_code, font=("Courier", 55, "bold"),
                     text_color="#1DB954").pack(side="left", padx=(0, 15))

        self.btn_copy = ctk.CTkButton(code_frame, text="📋", width=60, height=45, font=("Helvetica", 20),
                                      fg_color="#2D3436", hover_color="#636E72", command=self.copy_code)
        self.btn_copy.pack(side="left")

        # --- SETTINGS BEREICH ---
        self.settings_frame = ctk.CTkFrame(center_frame)
        self.settings_frame.pack(fill="x", pady=20)
        self.lbl_settings = ctk.CTkLabel(self.settings_frame, text="Lade Spieleinstellungen...", text_color="gray",
                                         font=("Helvetica", 14))
        self.lbl_settings.pack(pady=10, padx=20)

        if self.game_state.is_host:
            self.update_settings_ui()

        # --- SPIELERLISTE ---
        list_container = ctk.CTkFrame(center_frame, fg_color="transparent")
        list_container.pack(fill="x", pady=10)

        ctk.CTkLabel(list_container, text="SPIELER:", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 5))

        self.players_frame = ctk.CTkScrollableFrame(list_container, fg_color="#1e1e1e", width=450, height=180)
        self.players_frame.pack(fill="x")

        # --- ACTION BUTTONS ---
        self.action_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=(30, 0))

        if self.game_state.is_host:
            btn_center = ctk.CTkFrame(self.action_frame, fg_color="transparent")
            btn_center.pack(expand=True)

            self.btn_start = ctk.CTkButton(btn_center, text="SPIEL STARTEN", height=50, width=220,
                                           font=("Helvetica", 16, "bold"),
                                           fg_color="#1DB954", hover_color="#14833b", command=self.host_start_game)
            self.btn_start.pack(side="left", padx=10)

            self.btn_close = ctk.CTkButton(btn_center, text="LOBBY SCHLIESSEN", height=50, width=220,
                                           font=("Helvetica", 16, "bold"),
                                           fg_color="#c0392b", hover_color="#e74c3c", command=self.close_lobby)
            self.btn_close.pack(side="left", padx=10)
        else:
            self.lbl_wait = ctk.CTkLabel(self.action_frame, text="Warte auf Start durch den Host...",
                                         font=("Helvetica", 16, "bold"), text_color="orange")
            self.lbl_wait.pack(pady=(0, 15))

            self.btn_leave = ctk.CTkButton(self.action_frame, text="LOBBY VERLASSEN", height=50, width=250,
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
            self.btn_start.configure(text="MINDESTENS 2 SPIELER NÖTIG!", fg_color="#c0392b", hover_color="#e74c3c")
            self.after(2000, lambda: self.btn_start.configure(text="SPIEL STARTEN", fg_color="#1DB954",
                                                              hover_color="#14833b"))
            return

        self.network.send_signal("START_MATCH")
        self.router.start_game()

    def update_settings_ui(self):
        dist = "Ja" if self.game_state.distribute_time else "Nein"
        text = (f"Zeit: {self.game_state.start_time_minutes} Min | "
                f"Strafe: {self.game_state.penalty_seconds} Sek | "
                f"Aufteilen: {dist}\n"
                f"Projekt: {self.game_state.project_filename}")
        self.lbl_settings.configure(text=text, text_color="white")

    def update_player_list(self):
        for widget in self.players_frame.winfo_children():
            widget.destroy()

        for p in self.game_state.players:
            color = "#1DB954" if p in self.game_state.ready_players else "gray"
            display_text = f"• {p} (Host)" if p == self.game_state.players[0] else f"• {p}"
            ctk.CTkLabel(self.players_frame, text=display_text, font=("Helvetica", 18), text_color=color).pack(pady=5,
                                                                                                               anchor="w",
                                                                                                               padx=20)

    def _handle_name_taken(self):
        self.network.disconnect()
        messagebox.showerror("Fehler", "Dieser Name ist in der Lobby bereits vergeben. Bitte wähle einen anderen.")
        self.router.show_home()

    def _handle_lobby_closed(self):
        self.network.disconnect()
        messagebox.showinfo("Lobby geschlossen", "Der Host hat die Lobby geschlossen.")
        self.router.show_home()

    def _on_connected(self):
        if not self.game_state.is_host:
            logging.info("[LobbyView] Netzwerk verbunden. Sende Beitrittsanfrage...")
            self.network.send_signal("CLIENT_JOIN")

    def _on_client_join(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            logging.info(f"[LobbyView] Spieler {sender} möchte beitreten.")
            if sender in self.game_state.players:
                self.network.send_signal("NAME_TAKEN", data={"target": sender})
                return

            self.game_state.players.append(sender)
            self.game_state.active_players.append(sender)
            self.game_state.ready_players.add(sender)
            self.game_state.times[sender] = self.game_state.start_time_minutes * 60
            self.game_state.bonus_texts[sender] = ""

            self.update_player_list()

            sync_data = self.game_state.export_sync_data()
            self.network.send_signal("SYNC_STATE", data=sync_data)

    def _on_name_taken(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host:
            if data.get("target") == self.game_state.my_name:
                self._handle_name_taken()

    def _on_sync_state(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host:
            logging.info("[LobbyView] Synchronisiere Daten vom Host...")
            self.game_state.load_sync_data(data)
            self.game_state.ready_players = set(self.game_state.players)
            self.update_settings_ui()
            self.update_player_list()

    def _on_client_leave(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            logging.info(f"[LobbyView] Spieler {sender} hat die Lobby verlassen.")
            if sender in self.game_state.players: self.game_state.players.remove(sender)
            if sender in self.game_state.active_players: self.game_state.active_players.remove(sender)
            if sender in self.game_state.ready_players: self.game_state.ready_players.remove(sender)

            self.update_player_list()
            sync_data = self.game_state.export_sync_data()
            self.network.send_signal("SYNC_STATE", data=sync_data)

    def _on_lobby_closed(self):
        if not self.game_state.is_host:
            self._handle_lobby_closed()