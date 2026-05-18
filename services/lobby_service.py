# ================================================
# FILE: services/lobby_service.py
# ================================================
import logging
from core.event_bus import EventBus
from core.events import NetEvents, UIEvents
from services.base_service import BaseService


class LobbyService(BaseService):
    def __init__(self, game_state, network, workspace_service=None):
        super().__init__()
        self.game_state = game_state
        self.network = network
        self.workspace_service = workspace_service
        self._is_running = False

        self._listeners = {
            NetEvents.CONNECTED: self._on_connected,
            NetEvents.CLIENT_JOIN: self._on_client_join,
            NetEvents.NAME_TAKEN: self._on_name_taken,
            NetEvents.SYNC_STATE: self._on_sync_state,
            NetEvents.CLIENT_LEAVE: self._on_client_leave,
            NetEvents.FOLDER_VERIFIED: self._on_folder_verified,
            NetEvents.LOBBY_CLOSED: self._on_lobby_closed
        }

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        logging.info("[LobbyService] Gestartet. Verbinde mit Netzwerk...")

        self.register_listeners()

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

        self.cleanup()

    # --- NETZWERK & LOGIK HANDLER ---
    def _on_connected(self, data=None):
        if not self.game_state.is_host:
            self.network.send_signal("CLIENT_JOIN")

    def _on_client_join(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            if sender in self.game_state.players:
                self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
                return

            self.game_state.players.append(sender)
            self.game_state.active_players.append(sender)
            self.game_state.ready_players.add(sender)
            self.game_state.set_player_time(sender, self.game_state.start_time_minutes * 60)
            self.game_state.set_bonus_text(sender, "")

            self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
            EventBus.emit(UIEvents.LOBBY_REFRESH)

    def _on_name_taken(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host and data.get("target") == self.game_state.my_name:
            self._handle_cleanup()
            EventBus.emit(UIEvents.LOBBY_ERROR_NAME_TAKEN)

    def _on_sync_state(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host:
            self.game_state.load_sync_data(data)
            self.game_state.ready_players = set(self.game_state.players)

            # KISS & DRY: Da Rclone den Sync übernimmt und wir Sandboxing nutzen,
            # gibt es keine lokalen Handshakes mehr! Der Client ist sofort verifiziert.
            if self.game_state.my_name not in self.game_state.verified_players:
                self.network.send_signal("FOLDER_VERIFIED")

            EventBus.emit(UIEvents.LOBBY_SYNCED)
            EventBus.emit(UIEvents.LOBBY_REFRESH)

    def _on_client_leave(self, payload):
        sender = payload.get("sender")
        if self.game_state.is_host:
            if sender in self.game_state.players: self.game_state.players.remove(sender)
            if sender in self.game_state.active_players: self.game_state.active_players.remove(sender)
            if sender in self.game_state.ready_players: self.game_state.ready_players.remove(sender)
            if sender in self.game_state.verified_players: self.game_state.verified_players.remove(sender)

            self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
            EventBus.emit(UIEvents.LOBBY_REFRESH)

    def _on_folder_verified(self, payload):
        sender = payload.get("sender")
        if sender and self.game_state.is_host:
            if sender not in self.game_state.verified_players:
                self.game_state.verified_players.add(sender)
                self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
                EventBus.emit(UIEvents.LOBBY_REFRESH)

    def _on_lobby_closed(self, data=None):
        if not self.game_state.is_host:
            self._handle_cleanup()
            EventBus.emit(UIEvents.LOBBY_HOST_CLOSED)

    def _handle_cleanup(self):
        if self.workspace_service and self.game_state.room_code:
            self.workspace_service.cleanup_match_workspace(self.game_state.room_code)

        self._last_verified_ws = None
        self.network.disconnect()
        self.game_state.reset_match_data()