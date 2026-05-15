# ================================================
# FILE: core/match_controller.py
# ================================================
import time
import logging
from core.event_bus import EventBus
from core.events import CmdEvents, StateEvents, NetEvents, SysEvents, UIEvents
from services.match_export_service import MatchExportService


class MatchController:
    """
    Das Gehirn des Spiels.
    Verwaltet die Spielregeln (Zeiten, Strafen, Ausscheiden).
    """

    def __init__(self, game_state, network_manager):
        self.state = game_state
        self.network = network_manager

        self.last_update_time = None
        self.is_paused = False
        self._is_game_over = False
        self.last_finished_player = None

        # Typisierte Events statt Magic Strings!
        self._listeners = {
            CmdEvents.START_LOCAL_TURN: self._handle_local_turn_start,
            CmdEvents.TOGGLE_PAUSE: self._handle_toggle_pause,
            CmdEvents.END_TURN_SUCCESS: self._handle_turn_end_success,
            CmdEvents.END_TURN_ELIMINATED: self._handle_turn_end_eliminated,
            SysEvents.TICK: self._handle_tick,
            NetEvents.TURN_START: self._on_net_turn_start,
            NetEvents.PREPARE_SYNC: self._on_net_prepare_sync,
            NetEvents.TURN_END: self._on_net_turn_end,
            NetEvents.PAUSE: self._on_net_pause,
            NetEvents.RESUME: self._on_net_resume,
            NetEvents.ELIMINATED: self._on_net_eliminated,
            NetEvents.FINISHED: self._on_net_finished,
            NetEvents.CLIENT_LEAVE: self._on_net_client_leave
        }
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def cleanup(self):
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)

    def _handle_local_turn_start(self, data):
        self.state.active_player = self.state.my_name
        self.last_update_time = time.time()
        time_left = self.state.get_player_time(self.state.my_name)

        EventBus.emit(StateEvents.TURN_START,
                      data={"player": self.state.my_name, "time_left": time_left, "note": "DAW angeklickt"})
        self.network.send_signal("TURN_START", data={"remaining_time": time_left})

    def _handle_tick(self, data):
        if self._is_game_over: return

        if self.state.active_player and not self.is_paused:
            now = time.time()
            if self.last_update_time is None: self.last_update_time = now

            elapsed = now - self.last_update_time
            self.last_update_time = now
            self.state.update_time(self.state.active_player, elapsed)
            EventBus.emit(UIEvents.OBS_UPDATE, {"status": None})

        if self.state.active_player == self.state.my_name:
            time_left = self.state.get_player_time(self.state.my_name)
            EventBus.emit(StateEvents.TIMER_TICK, data={"time_left": time_left, "is_paused": self.is_paused})

            if time_left <= 0:
                EventBus.emit(StateEvents.TIME_UP)

    def _handle_toggle_pause(self, data):
        if self.state.active_player != self.state.my_name:
            return

        time_left = self.state.get_player_time(self.state.my_name)
        if not self.is_paused:
            self.is_paused = True
            EventBus.emit(StateEvents.PAUSED, data={"player": self.state.my_name, "time_left": time_left,
                                                    "note": "Nutzer hat Pause geklickt"})
            self.network.send_signal("PAUSE", data={"remaining_time": time_left})
        else:
            self.state.update_time(self.state.my_name, self.state.penalty_seconds)
            time_left = self.state.get_player_time(self.state.my_name)

            EventBus.emit(StateEvents.RESUMED, data={"player": self.state.my_name, "time_left": time_left,
                                                     "note": f"Fortgesetzt mit Strafe (-{self.state.penalty_seconds}s)"})
            self.is_paused = False
            self.last_update_time = time.time()
            self.network.send_signal("RESUME",
                                     data={"penalty": self.state.penalty_seconds, "remaining_time": time_left})

    def _handle_turn_end_success(self, data):
        file_hash = data.get("file_hash")
        time_left = self.state.get_player_time(self.state.my_name)
        self.last_finished_player = self.state.my_name

        if len(self.state.active_players) <= 1:
            EventBus.emit(StateEvents.FINISHED,
                          data={"player": self.state.my_name, "time_left": time_left, "note": "Als letzter abgegeben"})
            self.state.eliminate_player(self.state.my_name)
            self.network.send_signal("FINISHED",
                                     data={"remaining_time": time_left, "saved": True, "file_hash": file_hash})
            EventBus.emit(UIEvents.OBS_UPDATE, {"status": "FINISHED"})
            self._check_game_over()
        else:
            EventBus.emit(StateEvents.TURN_END,
                          data={"player": self.state.my_name, "time_left": time_left, "note": "Regulär abgegeben"})
            self.network.send_signal("TURN_END", data={"remaining_time": time_left, "file_hash": file_hash})
            EventBus.emit(UIEvents.OBS_UPDATE, {"status": "PAUSE / SYNCING"})

    def _handle_turn_end_eliminated(self, data):
        file_hash = data.get("file_hash")
        time_left = self.state.get_player_time(self.state.my_name)
        self.last_finished_player = self.state.my_name

        EventBus.emit(StateEvents.ELIMINATED,
                      data={"player": self.state.my_name, "time_left": time_left, "note": "Zeit abgelaufen"})
        self.state.eliminate_player(self.state.my_name)
        self.network.send_signal("ELIMINATED",
                                 data={"remaining_time": time_left, "saved": True, "file_hash": file_hash})
        EventBus.emit(UIEvents.OBS_UPDATE, {"status": "ELIMINATED"})
        self._check_game_over()

    def _check_game_over(self):
        if len(self.state.active_players) == 0:
            self._is_game_over = True
            EventBus.emit(UIEvents.OBS_UPDATE, {"status": "GAME OVER"})
            EventBus.emit(StateEvents.GAME_OVER, data={"note": "Alle Zeiten abgelaufen oder abgegeben"})

            EventBus.emit(CmdEvents.ANALYZE_MATCH, data={"game_state": self.state})

    def _on_net_turn_start(self, data):
        sender = data.get("sender")
        time_left = data.get("data", {}).get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit(StateEvents.TURN_START,
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler beginnt seinen Zug"})
        self.state.active_player = sender
        self.last_update_time = time.time()

    def _on_net_prepare_sync(self, data):
        sender = data.get("sender")
        self.state.active_player = None
        if "remaining_time" in data.get("data", {}): self.state.set_player_time(sender, data["data"]["remaining_time"])
        EventBus.emit(UIEvents.STATUS_UPDATE, data={"text": f"{sender} speichert...", "color": "orange"})

    def _on_net_turn_end(self, data):
        sender = data.get("sender")
        payload = data.get("data", {})
        time_left = payload.get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit(StateEvents.TURN_END,
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler hat abgegeben"})

        self.last_finished_player = sender
        if "remaining_time" in payload: self.state.set_player_time(sender, payload["remaining_time"])
        EventBus.emit(CmdEvents.WATCH_DOWNLOAD,
                      data={"expected_to_sync": True, "expected_hash": payload.get("file_hash"), "last_player": sender})

    def _on_net_pause(self, data):
        sender = data.get("sender")
        time_left = data.get("data", {}).get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit(StateEvents.PAUSED,
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler hat pausiert"})
        self.is_paused = True

    def _on_net_resume(self, data):
        sender = data.get("sender")
        payload = data.get("data", {})
        time_left = payload.get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit(StateEvents.RESUMED,
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler macht weiter"})

        self.state.update_time(sender, payload.get("penalty", 0))
        self.is_paused = False
        self.last_update_time = time.time()

    def _on_net_eliminated(self, data):
        sender = data.get("sender")
        payload = data.get("data", {})
        time_left = payload.get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit(StateEvents.ELIMINATED,
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler ist ausgeschieden"})

        self.last_finished_player = sender
        self.state.eliminate_player(sender)
        if "remaining_time" in payload: self.state.set_player_time(sender, payload["remaining_time"])
        EventBus.emit(CmdEvents.WATCH_DOWNLOAD,
                      data={"expected_to_sync": payload.get("saved", True), "expected_hash": payload.get("file_hash"),
                            "last_player": sender})

    def _on_net_finished(self, data):
        sender = data.get("sender")
        payload = data.get("data", {})
        time_left = payload.get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit(StateEvents.FINISHED,
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler ist als Sieger fertig"})

        self.last_finished_player = sender
        self.state.distribute_bonus_time(payload.get("remaining_time", 0))
        self.state.eliminate_player(sender)
        if "remaining_time" in payload: self.state.set_player_time(sender, payload["remaining_time"])
        EventBus.emit(CmdEvents.WATCH_DOWNLOAD,
                      data={"expected_to_sync": payload.get("saved", True), "expected_hash": payload.get("file_hash"),
                            "last_player": sender})

    def _on_net_client_leave(self, data):
        sender = data.get("sender")
        if not sender or sender not in self.state.players:
            return

        if sender in self.state.players:
            self.state.players.remove(sender)

        self.last_finished_player = sender
        self.state.eliminate_player(sender)
        EventBus.emit(StateEvents.ELIMINATED, data={"player": sender, "time_left": 0, "note": "Spiel verlassen"})

        if self.state.active_player == sender:
            self.state.active_player = None
            EventBus.emit(CmdEvents.WATCH_DOWNLOAD, data={
                "expected_to_sync": False,
                "expected_hash": None,
                "last_player": sender
            })

        self._check_game_over()

    def format_time(self, seconds):
        """Hilfsfunktion für die View, um Zeit zu formatieren"""
        return MatchExportService.format_time(seconds)