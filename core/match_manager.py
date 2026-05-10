# ================================================
# FILE: core/match_manager.py
# ================================================
import threading
from core.event_bus import EventBus
from core.match_controller import MatchController
from services.daw_service import DAWService
from services.sync_service import SyncService
from services.timeline_service import TimelineService
from utils.file_utils import get_template_path
from core.i18n import translate


class MatchManager:
    def __init__(self, game_state, network, router):
        self.game_state = game_state
        self.network = network
        self.router = router
        self._is_time_up = False

        self.daw_service = DAWService()
        self.sync_service = SyncService(self.game_state.local_project_path)
        self.timeline_service = TimelineService(self.game_state.local_match_dir, self.game_state.is_host)
        self.match_controller = MatchController(self.game_state, self.network, self.router)

        self._listeners = {
            "DAW_LAUNCH_SUCCESS": self._on_daw_started,
            "DAW_INTERACTION_DETECTED": self._start_my_timer,
            "DAW_PROCESS_CLOSED": self._process_turn_end,
            "SYNC_LOCK_RELEASED": self._on_sync_lock_released,
            "SYNC_LOCK_TIMEOUT": self._on_sync_lock_timeout,
            "SYNC_DOWNLOAD_COMPLETED": self._on_download_finished,
            "CMD_START_DOWNLOAD_WATCH": self._start_download_watcher,
            "STATE_TIME_UP": self._on_time_up
        }
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def cleanup(self):
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)

        self.match_controller.cleanup()
        self.daw_service.cleanup()
        self.sync_service.cleanup()
        self.timeline_service.cleanup()

    def start_match(self):
        EventBus.emit("STATE_MATCH_STARTED", data={"note": "Spiel gestartet, Initialisierung läuft"})
        if self.game_state.is_host:
            threading.Timer(1.0, self.auto_start_turn).start()

    def auto_start_turn(self):
        next_player = self.game_state.get_next_active_player(self.match_controller.last_finished_player)

        if not next_player:
            self.match_controller._check_game_over()
            return

        if next_player == self.game_state.my_name:
            actual_template = get_template_path(self.game_state.selected_template_path)
            EventBus.emit("UI_STATUS_UPDATE", data={"text": translate("status.opening_daw"), "color": "yellow"})
            EventBus.emit("CMD_LAUNCH_DAW", data={
                "project_path": self.game_state.local_project_path,
                "template_path": actual_template
            })
        else:
            EventBus.emit("UI_STATUS_UPDATE",
                          data={"text": translate("status.download_done_waiting").format(player=next_player), "color": "gray"})

    def _on_daw_started(self, data):
        EventBus.emit("UX_START_TURN")
        EventBus.emit("UI_STATUS_UPDATE", data={"text": translate("status.timer_starts_on_click"), "color": "yellow"})
        EventBus.emit("UX_SHOW_WARNING", data={"text": translate("status.waiting_for_click")})
        EventBus.emit("CMD_WAIT_DAW_INTERACTION")

    def _start_my_timer(self, data):
        EventBus.emit("CMD_START_LOCAL_TURN")
        self._is_time_up = False
        EventBus.emit("CMD_WAIT_DAW_EXIT")

    def _process_turn_end(self, data):
        if self.game_state.active_player != self.game_state.my_name: return

        self.game_state.active_player = None
        EventBus.emit("UX_END_TURN")

        time_left = self.game_state.get_player_time(self.game_state.my_name)
        EventBus.emit("UI_STATUS_UPDATE", data={"text": translate("status.saving_project"), "color": "yellow"})
        self.network.send_signal("PREPARE_SYNC", data={"remaining_time": time_left})

        EventBus.emit("CMD_WAIT_FOR_LOCK", data={"max_attempts": 100})

    def _on_sync_lock_timeout(self, data):
        EventBus.emit("UI_STATUS_UPDATE", data={"text": translate("status.err_reading_file"), "color": "red"})
        is_eliminated = self._is_time_up or (self.game_state.get_player_time(self.game_state.my_name) <= 0)
        EventBus.emit("CMD_END_TURN_ELIMINATED" if is_eliminated else "CMD_END_TURN_SUCCESS", data={"file_hash": None})

    def _on_sync_lock_released(self, data):
        EventBus.emit("UI_STATUS_UPDATE", data={"text": translate("status.checksum_calculated"), "color": "yellow"})
        is_eliminated = self._is_time_up or (self.game_state.get_player_time(self.game_state.my_name) <= 0)
        EventBus.emit("CMD_END_TURN_ELIMINATED" if is_eliminated else "CMD_END_TURN_SUCCESS",
                      data={"file_hash": data.get("hash")})

    def _start_download_watcher(self, data):
        if not data.get("expected_to_sync"):
            EventBus.emit("UI_STATUS_UPDATE",
                          data={"text": translate("status.player_gave_up").format(player=data.get('last_player')),
                                "color": "orange"})
            threading.Timer(2.0, self.auto_start_turn).start()
            return

        EventBus.emit("UI_STATUS_UPDATE",
                      data={"text": translate(
                          "status.player_finished_downloading").format(player=data.get('last_player')),
                            "color": "yellow"})
        EventBus.emit("CMD_WATCH_DOWNLOAD", data={"expected_hash": data.get("expected_hash")})

    def _on_download_finished(self, data):
        if data.get("success"):
            self.auto_start_turn()
        else:
            EventBus.emit("UI_STATUS_UPDATE", data={"text": translate("status.download_timeout"), "color": "red"})
            threading.Timer(2.0, self.auto_start_turn).start()

    def _on_time_up(self, data):
        if not self._is_time_up:
            self._is_time_up = True
            EventBus.emit("UI_STATUS_UPDATE",
                          data={"text": translate("status.auto_saving"), "color": "orange"})
            EventBus.emit("UX_SHOW_WARNING", data={"text": translate("status.auto_save_warning")})
            EventBus.emit("CMD_FORCE_AUTO_SAVE")