# ================================================
# FILE: services/lobby_service.py
# ================================================
import logging
from core.event_bus import EventBus
from services.base_service import BaseService


class LobbyService(BaseService):
    def __init__(self, game_state, network, workspace_service=None):
        super().__init__()
        self.game_state = game_state
        self.network = network
        self.workspace_service = workspace_service
        self._is_running = False
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
            EventBus.emit("UI_LOBBY_REFRESH")

    def _on_name_taken(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host and data.get("target") == self.game_state.my_name:
            self._handle_cleanup()
            EventBus.emit("UI_LOBBY_ERROR_NAME_TAKEN")

    def _on_sync_state(self, payload):
        data = payload.get("data", {})
        if not self.game_state.is_host:
            self.game_state.load_sync_data(data)
            self.game_state.ready_players = set(self.game_state.players)

            EventBus.emit("UI_LOBBY_SYNCED")
            EventBus.emit("UI_LOBBY_REFRESH")

            workspace_id = self.game_state.workspace_id
            is_verified_by_host = self.game_state.my_name in self.game_state.verified_players

            if workspace_id and not is_verified_by_host:
                if self._last_verified_ws != workspace_id:
                    self._last_verified_ws = workspace_id
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
            if sender not in self.game_state.verified_players:
                self.game_state.verified_players.add(sender)
                self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
                EventBus.emit("UI_LOBBY_REFRESH")

    def _on_lobby_closed(self, data=None):
        if not self.game_state.is_host:
            self._handle_cleanup()
            EventBus.emit("UI_LOBBY_HOST_CLOSED")

    def _on_workspace_ready(self, data):
        if self.game_state.is_host:
            self.game_state.workspace_id = data.get("workspace_id", "")
            self.game_state.verified_players.add(self.game_state.my_name)

            if self.network.is_connected:
                self.network.send_signal("SYNC_STATE", data=self.game_state.export_sync_data())
            EventBus.emit("UI_LOBBY_REFRESH")

    def _on_local_handshake_success(self, data=None):
        if not self.game_state.is_host:
            self.game_state.verified_players.add(self.game_state.my_name)
            self.network.send_signal("FOLDER_VERIFIED")
            EventBus.emit("UI_LOBBY_REFRESH")

    def _on_handshake_timeout(self, data=None):
        if not self.game_state.is_host:
            self.network.send_signal("CLIENT_LEAVE")
            self._handle_cleanup()
            EventBus.emit("UI_LOBBY_ERROR_HANDSHAKE")

    def _handle_cleanup(self):
        self._last_verified_ws = None
        self.network.disconnect()
        self.game_state.reset_match_data()