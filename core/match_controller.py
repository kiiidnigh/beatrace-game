import time
import os
import logging
from core.event_bus import EventBus
from utils.file_utils import get_obs_path


class MatchController:
    """
    Das Gehirn des Spiels.
    Verwaltet die Spielregeln (Zeiten, Strafen, Ausscheiden) und schreibt die OBS Dateien.
    """

    def __init__(self, game_state, network_manager, router):
        self.state = game_state
        self.network = network_manager
        self.router = router

        safe_name = self.state.my_name.replace(" ", "_").lower()
        self.obs_file_path = get_obs_path(safe_name)

        self.last_update_time = None
        self.is_paused = False
        self._is_game_over = False
        self.last_finished_player = None

        self._listeners = {
            "CMD_START_LOCAL_TURN": self._handle_local_turn_start,
            "CMD_TOGGLE_PAUSE": self._handle_toggle_pause,
            "CMD_END_TURN_SUCCESS": self._handle_turn_end_success,
            "CMD_END_TURN_ELIMINATED": self._handle_turn_end_eliminated,
            "SYS_TICK": self._handle_tick,
            "NET_TURN_START": self._on_net_turn_start,
            "NET_PREPARE_SYNC": self._on_net_prepare_sync,
            "NET_TURN_END": self._on_net_turn_end,
            "NET_PAUSE": self._on_net_pause,
            "NET_RESUME": self._on_net_resume,
            "NET_ELIMINATED": self._on_net_eliminated,
            "NET_FINISHED": self._on_net_finished,
            "NET_CLIENT_LEAVE": self._on_net_client_leave  # <--- NEU: Überwacht Verbindungsabbrüche im Match
        }
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def cleanup(self):
        """Meldet den Controller sicher vom Event-System ab."""
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)

    def _handle_local_turn_start(self, data):
        logging.info("[MatchController] Lokaler Zug gestartet.")
        self.state.active_player = self.state.my_name
        self.last_update_time = time.time()
        time_left = self.state.get_player_time(self.state.my_name)

        EventBus.emit("STATE_TURN_START",
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
            self._write_obs_file()

        if self.state.active_player == self.state.my_name:
            time_left = self.state.get_player_time(self.state.my_name)
            EventBus.emit("STATE_TIMER_TICK", data={"time_left": time_left, "is_paused": self.is_paused})

            if time_left <= 0:
                EventBus.emit("STATE_TIME_UP")

    def _handle_toggle_pause(self, data):
        # FIX: Ein Spieler darf nur pausieren, wenn er WIRKLICH am Zug ist!
        if self.state.active_player != self.state.my_name:
            return

        time_left = self.state.get_player_time(self.state.my_name)
        if not self.is_paused:
            self.is_paused = True
            EventBus.emit("STATE_PAUSED", data={"player": self.state.my_name, "time_left": time_left,
                                                "note": "Nutzer hat Pause geklickt"})
            self.network.send_signal("PAUSE", data={"remaining_time": time_left})
        else:
            self.state.update_time(self.state.my_name, self.state.penalty_seconds)
            time_left = self.state.get_player_time(self.state.my_name)

            EventBus.emit("STATE_RESUMED", data={"player": self.state.my_name, "time_left": time_left,
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
            EventBus.emit("STATE_FINISHED",
                          data={"player": self.state.my_name, "time_left": time_left, "note": "Als letzter abgegeben"})
            self.state.eliminate_player(self.state.my_name)
            self.network.send_signal("FINISHED",
                                     data={"remaining_time": time_left, "saved": True, "file_hash": file_hash})
            self._write_obs_file("FINISHED")
            self._check_game_over()
        else:
            EventBus.emit("STATE_TURN_END",
                          data={"player": self.state.my_name, "time_left": time_left, "note": "Regulär abgegeben"})
            self.network.send_signal("TURN_END", data={"remaining_time": time_left, "file_hash": file_hash})
            self._write_obs_file("PAUSE / SYNCING")

    def _handle_turn_end_eliminated(self, data):
        file_hash = data.get("file_hash")
        time_left = self.state.get_player_time(self.state.my_name)
        self.last_finished_player = self.state.my_name

        EventBus.emit("STATE_ELIMINATED",
                      data={"player": self.state.my_name, "time_left": time_left, "note": "Zeit abgelaufen"})
        self.state.eliminate_player(self.state.my_name)
        self.network.send_signal("ELIMINATED",
                                 data={"remaining_time": time_left, "saved": True, "file_hash": file_hash})
        self._write_obs_file("ELIMINATED")
        self._check_game_over()

    def _check_game_over(self):
        if len(self.state.active_players) == 0:
            self._is_game_over = True
            EventBus.emit("STATE_GAME_OVER", data={"note": "Alle Zeiten abgelaufen oder abgegeben"})
            self._write_obs_file("GAME OVER")

            # DRY: Wir analysieren das Projekt exakt EINMAL und cachen es global!
            from services.flp_analyzer_service import FLPAnalyzerService
            self.state.match_stats = FLPAnalyzerService.analyze_match(self.state)

            if self.state.is_host:
                self._generate_match_files()

            self.router.show_finish()

    def _on_net_turn_start(self, data):
        sender = data.get("sender")
        time_left = data.get("data", {}).get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit("STATE_TURN_START",
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler beginnt seinen Zug"})
        self.state.active_player = sender
        self.last_update_time = time.time()

    def _on_net_prepare_sync(self, data):
        sender = data.get("sender")
        self.state.active_player = None
        if "remaining_time" in data.get("data", {}): self.state.set_player_time(sender, data["data"]["remaining_time"])
        EventBus.emit("UI_STATUS_UPDATE", data={"text": f"{sender} speichert...", "color": "orange"})

    def _on_net_turn_end(self, data):
        sender = data.get("sender")
        payload = data.get("data", {})
        time_left = payload.get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit("STATE_TURN_END",
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler hat abgegeben"})

        self.last_finished_player = sender
        if "remaining_time" in payload: self.state.set_player_time(sender, payload["remaining_time"])
        EventBus.emit("CMD_START_DOWNLOAD_WATCH",
                      data={"expected_to_sync": True, "expected_hash": payload.get("file_hash"), "last_player": sender})

    def _on_net_pause(self, data):
        sender = data.get("sender")
        time_left = data.get("data", {}).get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit("STATE_PAUSED",
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler hat pausiert"})
        self.is_paused = True

    def _on_net_resume(self, data):
        sender = data.get("sender")
        payload = data.get("data", {})
        time_left = payload.get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit("STATE_RESUMED",
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler macht weiter"})

        self.state.update_time(sender, payload.get("penalty", 0))
        self.is_paused = False
        self.last_update_time = time.time()

    def _on_net_eliminated(self, data):
        sender = data.get("sender")
        payload = data.get("data", {})
        time_left = payload.get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit("STATE_ELIMINATED",
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler ist ausgeschieden"})

        self.last_finished_player = sender
        self.state.eliminate_player(sender)
        if "remaining_time" in payload: self.state.set_player_time(sender, payload["remaining_time"])
        EventBus.emit("CMD_START_DOWNLOAD_WATCH",
                      data={"expected_to_sync": payload.get("saved", True), "expected_hash": payload.get("file_hash"),
                            "last_player": sender})

    def _on_net_finished(self, data):
        sender = data.get("sender")
        payload = data.get("data", {})
        time_left = payload.get("remaining_time", self.state.get_player_time(sender))
        EventBus.emit("STATE_FINISHED",
                      data={"player": sender, "time_left": time_left, "note": "Anderer Spieler ist als Sieger fertig"})

        self.last_finished_player = sender
        self.state.distribute_bonus_time(payload.get("remaining_time", 0))
        self.state.eliminate_player(sender)
        if "remaining_time" in payload: self.state.set_player_time(sender, payload["remaining_time"])
        EventBus.emit("CMD_START_DOWNLOAD_WATCH",
                      data={"expected_to_sync": payload.get("saved", True), "expected_hash": payload.get("file_hash"),
                            "last_player": sender})

    def _on_net_client_leave(self, data):
        # FIX: Behandelt Spielabbrüche während des Matches richtig
        sender = data.get("sender")
        if not sender or sender not in self.state.players:
            return

        logging.info(f"[MatchController] Spieler {sender} hat das laufende Spiel verlassen.")

        # Komplett aus der Spielerliste entfernen, damit er in der Lobby nicht mehr auftaucht!
        if sender in self.state.players:
            self.state.players.remove(sender)

        self.last_finished_player = sender
        self.state.eliminate_player(sender)
        EventBus.emit("STATE_ELIMINATED", data={"player": sender, "time_left": 0, "note": "Spiel verlassen"})

        # Falls der Spieler gerade an der Reihe war, sofort abbrechen und Runde weitergeben
        if self.state.active_player == sender:
            self.state.active_player = None
            # Es gibt kein neues Projekt, deshalb überspringen wir den File-Watcher komplett
            EventBus.emit("CMD_START_DOWNLOAD_WATCH", data={
                "expected_to_sync": False,
                "expected_hash": None,
                "last_player": sender
            })

        self._check_game_over()

    def format_time(self, seconds):
        if seconds < 0: seconds = 0
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 10)
        return f"{mins:02d}:{secs:02d}.{millis}"

    def _write_obs_file(self, status=None):
        try:
            with open(self.obs_file_path, "w") as f:
                if status:
                    f.write(status)
                else:
                    all_times = self.state.get_all_times_dict()
                    obs_text = " | ".join([f"{p}: {self.format_time(all_times.get(p, 0))}" for p in self.state.players])
                    active = f"[{self.state.active_player}] " if self.state.active_player else "[PAUSE] "
                    f.write(active + obs_text)
        except Exception:
            pass

    def _generate_match_files(self):
        match_dir = self.state.local_match_dir
        os.makedirs(match_dir, exist_ok=True)
        try:
            with open(os.path.join(match_dir, "summary.txt"), "w", encoding="utf-8") as f:
                f.write("=== BEATRACE ZUSAMMENFASSUNG ===\n\n")

                f.write("[ SPIELER & ZEITEN ]\n")
                all_times = self.state.get_all_times_dict()
                for p in self.state.players:
                    f.write(f"- {p} (Restzeit: {self.format_time(all_times.get(p, 0))})\n")

                f.write("\n[ MATCH AWARDS ]\n")
                awards = self.state.match_stats.get("awards", {})
                if awards:
                    for title, winner in awards.items():
                        # Entfernt Emojis für die saubere TXT-Ausgabe
                        clean_title = title.split(" ", 1)[-1] if " " in title else title
                        f.write(f"- {clean_title}: {winner}\n")
                else:
                    f.write("- Keine Auszeichnungen generiert.\n")

                f.write("\n[ PROJEKT FAKTEN ]\n")
                f.write(f"- Dateigröße: {self.state.match_stats.get('file_size', '0.00 MB')}\n")
                f.write(f"- FL Studio Version: {self.state.match_stats.get('fl_version', 'Unbekannt')}\n")

                project_data = self.state.match_stats.get("project_data", {})
                if project_data:
                    for key, val in project_data.items():
                        # Emojis filtern
                        clean_key = key.split(" ", 1)[-1] if " " in key else key
                        f.write(f"- {clean_key}: {val}\n")
                else:
                    f.write("- Keine detaillierten Metadaten verfügbar.\n")

        except Exception as e:
            logging.error(f"[MatchController] Fehler beim Schreiben der summary.txt: {e}")