# ================================================
# FILE: core/match_manager.py
# ================================================
import threading
from core.event_bus import EventBus
from core.events import CmdEvents, UIEvents, StateEvents
from core.match_controller import MatchController
from services.daw_service import DAWService
from services.sync_service import SyncService
from services.timeline_service import TimelineService
from services.match_export_service import MatchExportService
from services.workspace_service import WorkspaceService
from services.storage.rclone_adapter import RcloneCloudAdapter
from utils.file_utils import get_template_path
from core.i18n import translate


class MatchManager:
    def __init__(self, game_state, network, router):
        self.game_state = game_state
        self.network = network
        self.router = router
        self._is_time_up = False

        # SRP & KISS: Workspace vorbereiten (Sandboxing in AppData)
        self.workspace_service = WorkspaceService()
        self.workspace_service.setup_match_workspace(self.game_state)

        self.daw_service = DAWService()

        # OCP: Cloud Adapter instanziieren und injizieren
        self.storage_adapter = RcloneCloudAdapter()

        # DRY & Fail Fast: Nutze den vom Host per MQTT übermittelten Pfad
        if not self.game_state.cloud_remote_path:
            import logging
            logging.error("[MatchManager] CRITICAL: Kein Cloud-Pfad vom Host empfangen!")
            # Letzter Rettungsanker, damit das Spiel nicht hart abstürzt
            self.game_state.cloud_remote_path = f"Beatrace-Matches/Match_{self.game_state.room_code}/{self.game_state.project_filename}"

        self.sync_service = SyncService(
            local_path=self.game_state.local_project_path,
            remote_path=self.game_state.cloud_remote_path,
            storage_adapter=self.storage_adapter
        )

        self.timeline_service = TimelineService(self.game_state.local_match_dir, self.game_state.is_host)
        self.match_controller = MatchController(self.game_state, self.network)
        self.match_export_service = MatchExportService(self.game_state)

        self._listeners = {
            "DAW_LAUNCH_SUCCESS": self._on_daw_started,
            "DAW_INTERACTION_DETECTED": self._start_my_timer,
            "DAW_PROCESS_CLOSED": self._process_turn_end,
            "SYNC_LOCK_RELEASED": self._on_sync_lock_released,
            "SYNC_LOCK_TIMEOUT": self._on_sync_lock_timeout,
            "SYNC_DOWNLOAD_COMPLETED": self._on_download_finished,
            CmdEvents.WATCH_DOWNLOAD: self._start_download_watcher,
            StateEvents.TIME_UP: self._on_time_up
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
        self.match_export_service.cleanup()

    def start_match(self):
        EventBus.emit(StateEvents.MATCH_STARTED, data={"note": "Spiel gestartet, Initialisierung läuft"})
        if self.game_state.is_host:
            threading.Timer(1.0, self.auto_start_turn).start()

    def auto_start_turn(self):
        next_player = self.game_state.get_next_active_player(self.match_controller.last_finished_player)

        if not next_player:
            self.match_controller._check_game_over()
            return

        if next_player == self.game_state.my_name:
            actual_template = get_template_path(self.game_state.selected_template_path)
            EventBus.emit(UIEvents.STATUS_UPDATE, data={"text": translate("status.opening_daw"), "color": "yellow"})
            EventBus.emit(CmdEvents.LAUNCH_DAW, data={
                "project_path": self.game_state.local_project_path,
                "template_path": actual_template
            })
        else:
            EventBus.emit(UIEvents.STATUS_UPDATE,
                          data={"text": translate("status.download_done_waiting").format(player=next_player),
                                "color": "gray"})

    def _on_daw_started(self, data):
        EventBus.emit(UIEvents.UX_START_TURN)
        EventBus.emit(UIEvents.STATUS_UPDATE,
                      data={"text": translate("status.timer_starts_on_click"), "color": "yellow"})
        EventBus.emit(UIEvents.UX_SHOW_WARNING, data={"text": translate("status.waiting_for_click")})
        EventBus.emit(CmdEvents.WAIT_DAW_INTERACTION)

    def _start_my_timer(self, data):
        EventBus.emit(CmdEvents.START_LOCAL_TURN)
        self._is_time_up = False
        EventBus.emit(CmdEvents.WAIT_DAW_EXIT)

    def _process_turn_end(self, data):
        if self.game_state.active_player != self.game_state.my_name: return

        self.game_state.active_player = None
        EventBus.emit(UIEvents.UX_END_TURN)

        time_left = self.game_state.get_player_time(self.game_state.my_name)

        # WICHTIG: Sofortiges Feedback ans Netzwerk schicken, damit bei den anderen die Timer pausieren!
        self.network.send_signal("PREPARE_SYNC", data={"remaining_time": time_left})

        # Warten auf Dateifreigabe (und anschließenden Rclone Upload)
        EventBus.emit(CmdEvents.WAIT_FOR_LOCK, data={"max_attempts": 100})

    def _on_sync_lock_timeout(self, data):
        EventBus.emit(UIEvents.STATUS_UPDATE, data={"text": "Speicher- / Cloud-Fehler!", "color": "red"})
        is_eliminated = self._is_time_up or (self.game_state.get_player_time(self.game_state.my_name) <= 0)
        EventBus.emit(CmdEvents.END_TURN_ELIMINATED if is_eliminated else CmdEvents.END_TURN_SUCCESS,
                      data={"file_hash": None})

    def _on_sync_lock_released(self, data):
        EventBus.emit(UIEvents.STATUS_UPDATE, data={"text": "Projekt gesichert & hochgeladen!", "color": "yellow"})
        is_eliminated = self._is_time_up or (self.game_state.get_player_time(self.game_state.my_name) <= 0)

        # Sende den Turn_End inkl Hash über das Netzwerk
        EventBus.emit(CmdEvents.END_TURN_ELIMINATED if is_eliminated else CmdEvents.END_TURN_SUCCESS,
                      data={"file_hash": data.get("hash")})

    def _start_download_watcher(self, data):
        # Wir kümmern uns hier NUR NOCH um den Fall, dass KEIN Download nötig ist.
        # Wenn einer nötig ist (True), fängt der SyncService das Event selbstständig ab.
        if not data.get("expected_to_sync", True):
            EventBus.emit(UIEvents.STATUS_UPDATE,
                          data={"text": translate("status.player_gave_up").format(player=data.get('last_player')),
                                "color": "orange"})
            threading.Timer(2.0, self.auto_start_turn).start()

    def _on_download_finished(self, data):
        if data.get("success"):
            self.auto_start_turn()
        else:
            EventBus.emit(UIEvents.STATUS_UPDATE, data={"text": "Cloud-Download fehlgeschlagen!", "color": "red"})
            threading.Timer(2.0, self.auto_start_turn).start()

    def _on_time_up(self, data):
        if not self._is_time_up:
            self._is_time_up = True
            EventBus.emit(UIEvents.STATUS_UPDATE,
                          data={"text": translate("status.auto_saving"), "color": "orange"})
            EventBus.emit(UIEvents.UX_SHOW_WARNING, data={"text": translate("status.auto_save_warning")})
            EventBus.emit(CmdEvents.FORCE_AUTO_SAVE)