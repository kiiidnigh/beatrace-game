# ================================================
# FILE: services/lobby_service.py
# ================================================
import logging
from core.event_bus import EventBus


class LobbyService:
    """
    Kapselt die gesamte Business- und Netzwerklogik für die Lobby-Phase.
    Trennt den Status vom UI (Separation of Concerns).
    """

    def __init__(self, game_state, network):
        self.game_state = game_state
        self.network = network
        self._is_running = False

        # Loop-Breaker: Merkt sich den zuletzt geprüften Workspace des Clients
        self._last_verified_ws = None

        self._listeners = {
            "NET_CONNECTED": self._on_connected,
            "NET_CLIENT_JOIN": self._on_client_join,
            "NET_NAME_TAKEN": self._on_name_taken,
            "NET_SYNC_STATE": self._on_sync_state,
            "NET_CLIENT_LEAVE": self._on_client_leave,
            "NET_FOLDER_VERIFIED": self._on_folder_verified,
            "NET_LOBBY_CLOSED": self._on_lobby_closed,
            "SYS_WORKSPACE_READY": self._on_workspace_ready,
            "SYS_HANDSHAKE_SUCCESS": self._on_local_handshake_success,
            "SYS_HANDSHAKE_TIMEOUT": self._on_handshake_timeout
        }

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        logging.info("[LobbyService] Gestartet. Verbinde mit Netzwerk...")

        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

        # FIX: Wenn das Netzwerk bereits durch das erste Match verbunden ist,
        # müssen wir den Sync/Join-Befehl manuell anstoßen, da NET_CONNECTED nicht erneut feuert.
        if not self.network.is_connected:
            self.network.connect(self.game_state.my_name, self.game_state.room_code)
        else:
            if self.game_state.is_host:
                self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
            else:
                self.network.send_signal("CLIENT_JOIN")

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        logging.info("[LobbyService] Gestoppt.")

        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)

    # --- NETZWERK & LOGIK HANDLER ---

    def _on_connected(self, data=None):
        if not self.game_state.is_host:
            # Client betritt den Raum
            self.network.send_signal("CLIENT_JOIN")

    def _on_client_join(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            # Schutz vor doppelten Namen / Resync für zurückkehrende Spieler
            if sender in self.game_state.players:
                # FIX: Wenn der Spieler für ein neues Match in die Lobby zurückkehrt,
                # befindet er sich bereits in der Liste. Wir blockieren ihn nicht,
                # sondern schicken ihm einfach die neuen Sync-Daten für den nächsten Workspace!
                self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
                return

            # Neuen Spieler registrieren
            self.game_state.players.append(sender)
            self.game_state.active_players.append(sender)
            self.game_state.ready_players.add(sender)
            self.game_state.set_player_time(sender, self.game_state.start_time_minutes * 60)
            self.game_state.set_bonus_text(sender, "")

            # Den neuen Status an alle verteilen
            self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
            EventBus.emit("UI_LOBBY_REFRESH")

    def _on_name_taken(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host and data.get("target") == self.game_state.my_name:
            self._handle_cleanup()
            EventBus.emit("UI_LOBBY_ERROR_NAME_TAKEN")

    def _on_sync_state(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host:
            # Client lädt den Status vom Host
            self.game_state.load_sync_data(data)

            # Alle sind sofort ready in der Lobby
            self.game_state.ready_players = set(self.game_state.players)

            EventBus.emit("UI_LOBBY_SYNCED")  # Stoppt den UI Lade-Timer
            EventBus.emit("UI_LOBBY_REFRESH")

            # LOOP-BREAKER (Client-Seite):
            # Verifizierung nur auslösen, wenn wir vom Host nicht als verifiziert gemeldet wurden
            # UND wir diesen Workspace-Code nicht schon lokal geprüft haben.
            workspace_id = self.game_state.workspace_id
            is_verified_by_host = self.game_state.my_name in self.game_state.verified_players

            if workspace_id and not is_verified_by_host:
                if self._last_verified_ws != workspace_id:
                    self._last_verified_ws = workspace_id
                    # Löst asynchron die Signatur-Prüfung auf der Festplatte aus
                    EventBus.emit("CMD_VERIFY_WORKSPACE", data={
                        "base_folder": self.game_state.local_drive_folder,
                        "workspace_id": workspace_id
                    })

    def _on_client_leave(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            if sender in self.game_state.players: self.game_state.players.remove(sender)
            if sender in self.game_state.active_players: self.game_state.active_players.remove(sender)
            if sender in self.game_state.ready_players: self.game_state.ready_players.remove(sender)
            if sender in self.game_state.verified_players: self.game_state.verified_players.remove(sender)

            self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
            EventBus.emit("UI_LOBBY_REFRESH")

    def _on_folder_verified(self, payload):
        sender = payload.get("sender")
        if sender and self.game_state.is_host:
            # LOOP-BREAKER (Host-Seite):
            # Nur pushen, wenn der Spieler wirklich *neu* verifiziert wird.
            if sender not in self.game_state.verified_players:
                self.game_state.verified_players.add(sender)
                # Host pusht den verifizierten Status an alle Clients
                self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
                EventBus.emit("UI_LOBBY_REFRESH")

    def _on_lobby_closed(self, data=None):
        if not self.game_state.is_host:
            self._handle_cleanup()
            EventBus.emit("UI_LOBBY_HOST_CLOSED")

    # --- SYSTEM & WORKSPACE HANDLER ---

    def _on_workspace_ready(self, data):
        """Wird ausgelöst, wenn der Host eine Match-Runde (neu) generiert hat."""
        if self.game_state.is_host:
            self.game_state.workspace_id = data.get("workspace_id", "")

            # Host markiert sich selbst als verifiziert, wenn er einen neuen Workspace erstellt
            self.game_state.verified_players.add(self.game_state.my_name)

            if self.network.is_connected:
                # Neuen Workspace sofort an die Clients in der Lobby pushen
                self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
            EventBus.emit("UI_LOBBY_REFRESH")

    def _on_local_handshake_success(self, data=None):
        """Wird ausgelöst, wenn der Client-Ordner mit der Host-ID übereinstimmt."""
        if not self.game_state.is_host:
            self.game_state.verified_players.add(self.game_state.my_name)
            self.network.send_signal("FOLDER_VERIFIED")
            EventBus.emit("UI_LOBBY_REFRESH")

    def _on_handshake_timeout(self, data=None):
        """Wird ausgelöst, wenn der Client-Ordner falsch ist."""
        if not self.game_state.is_host:
            self.network.send_signal("CLIENT_LEAVE")
            self._handle_cleanup()
            EventBus.emit("UI_LOBBY_ERROR_HANDSHAKE")

    def _handle_cleanup(self):
        """Interne Hilfsfunktion, um bei Fehlern aufzuräumen."""
        self._last_verified_ws = None
        self.network.disconnect()
        self.game_state.reset_match_data()