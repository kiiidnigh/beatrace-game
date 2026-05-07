import customtkinter as ctk
from utils.file_utils import load_prefs, get_template_path

from core.event_bus import EventBus
from core.match_controller import MatchController
from services.ux_service import UXService
from services.daw_service import DAWService
from services.sync_service import SyncService
from services.timeline_service import TimelineService


class GameView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router=None, **kwargs):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router
        self.player_labels = {}
        self._is_time_up = False

        EventBus.clear_all()

        ui_mode = load_prefs().get("ui_mode", "Standard")

        self.ux_service = UXService(ui_mode, self.winfo_toplevel(), self.game_state)
        self.daw_service = DAWService()
        self.sync_service = SyncService(self.game_state.local_project_path)
        self.timeline_service = TimelineService(self.game_state.local_match_dir, self.game_state.is_host)

        self.match_controller = MatchController(self.game_state, self.network, self.router)

        self._setup_event_listeners()
        self.setup_ui()

        self._ui_tick()

        EventBus.emit("STATE_MATCH_STARTED", data={"note": "Spiel gestartet, Initialisierung läuft"})

        if self.game_state.is_host:
            self.after(1000, self._auto_start_my_turn)
        else:
            if self.game_state.players:
                self.status_label.configure(text=f"Spiel gestartet! {self.game_state.players[0]} lädt das Projekt...",
                                            text_color="white")

    def _setup_event_listeners(self):
        EventBus.subscribe("STATE_TURN_START", lambda d: self.after(0, self._ui_on_turn_start, d))
        EventBus.subscribe("STATE_PAUSED", lambda d: self.after(0, self._ui_on_pause, d))
        EventBus.subscribe("STATE_RESUMED", lambda d: self.after(0, self._ui_on_resume, d))
        EventBus.subscribe("STATE_TIMER_TICK", lambda d: self.after(0, self._ui_on_timer_tick, d))
        EventBus.subscribe("STATE_TIME_UP", lambda d: self.after(0, self._ui_on_time_up))
        EventBus.subscribe("STATE_GAME_OVER", lambda d: self.after(0, self._ui_on_game_over))

        EventBus.subscribe("STATE_TURN_END", lambda d: self.after(0, lambda: self.status_label.configure(
            text="Zug abgegeben! Warte auf Sync...", text_color="orange")))
        EventBus.subscribe("STATE_ELIMINATED", lambda d: self.after(0, lambda: self.status_label.configure(
            text="Ausgeschieden!", text_color="red")))

        EventBus.subscribe("UI_STATUS_UPDATE", lambda d: self.after(0, lambda: self.status_label.configure(
            text=d.get("text"), text_color=d.get("color", "white"))))

        EventBus.subscribe("DAW_LAUNCH_SUCCESS", lambda d: self.after(0, self._on_daw_started))
        EventBus.subscribe("DAW_LAUNCH_ERROR", lambda d: self.after(0, lambda: self.status_label.configure(
            text=d.get("error"), text_color="red")))
        EventBus.subscribe("DAW_INTERACTION_DETECTED", lambda d: self.after(0, self._start_my_timer_ui))
        EventBus.subscribe("DAW_PROCESS_CLOSED", lambda d: self.after(0, self._process_turn_end))

        # Hört auf den Klick beim Fortsetzen
        EventBus.subscribe("DAW_RESUME_CLICK_DETECTED", lambda d: self.after(0, self._on_resume_click))

        EventBus.subscribe("SYNC_LOCK_RELEASED", lambda d: self.after(0, self._on_sync_lock_released, d))
        EventBus.subscribe("SYNC_LOCK_TIMEOUT", lambda d: self.after(0, self._on_sync_lock_timeout))
        EventBus.subscribe("SYNC_DOWNLOAD_COMPLETED", lambda d: self.after(0, self._on_download_finished, d))
        EventBus.subscribe("CMD_START_DOWNLOAD_WATCH", lambda d: self.after(0, self._start_download_watcher, d))

    def setup_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(header_frame, text="Beatrace läuft!", font=("Helvetica", 24, "bold")).pack(side="left")
        ctk.CTkButton(header_frame, text="Verlassen", width=100, height=40, font=("Helvetica", 14),
                      fg_color="#c0392b", hover_color="#e74c3c", command=self.leave_game).pack(side="right")

        self.status_label = ctk.CTkLabel(self, text="Initialisiere...", text_color="gray",
                                         font=("Helvetica", 18, "bold"))
        self.status_label.pack(pady=10)

        main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.labels_frame = ctk.CTkFrame(main_content_frame)
        self.labels_frame.pack(expand=True, padx=20, pady=20)

        for player in self.game_state.players:
            lbl = ctk.CTkLabel(self.labels_frame, text=f"{player}: --:--", font=("Helvetica", 32, "bold"))
            lbl.pack(pady=15, padx=40)
            self.player_labels[player] = lbl

        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(fill="x", side="bottom", pady=(10, 30))

        self.btn_pause = ctk.CTkButton(self.control_frame, text="PAUSE", width=250, height=50, state="disabled",
                                       font=("Helvetica", 16, "bold"),
                                       command=lambda: EventBus.emit("CMD_TOGGLE_PAUSE"))
        self.btn_pause.pack(expand=True)

    def _ui_tick(self):
        EventBus.emit("SYS_TICK")
        self.update_ui_text()
        self.after(100, self._ui_tick)

    def _ui_on_turn_start(self, data):
        player = data.get("player")
        if player == self.game_state.my_name:
            self.status_label.configure(text="Dein Zug läuft! (Schließe DAW zum Abgeben)", text_color="#1DB954")
        else:
            self.status_label.configure(text=f"{player}'s Zug läuft...", text_color="white")

    def _ui_on_pause(self, data):
        player = data.get("player")
        if player == self.game_state.my_name:
            # Button sperren und Nutzer auffordern zu klicken
            self.btn_pause.configure(text=f"KLICKE ZUM FORTSETZEN (-{self.game_state.penalty_seconds}s)",
                                     fg_color="#e67e22", state="disabled")
            # Minimales Delay, damit das Loslassen des Pause-Buttons nicht sofort als "Resume-Klick" gewertet wird
            self.after(500, lambda: EventBus.emit("CMD_WAIT_RESUME_CLICK"))

        self.status_label.configure(text=f"PAUSIERT", text_color="#e67e22")

    def _ui_on_resume(self, data):
        player = data.get("player")
        if player == self.game_state.my_name:
            # Button wieder in den Normalzustand versetzen
            self.btn_pause.configure(state="normal", text="PAUSE", fg_color=["#3a7ebf", "#1f538d"])
            self.status_label.configure(text="Dein Zug läuft!", text_color="#1DB954")
        else:
            self.status_label.configure(text=f"{player}'s Zug läuft...", text_color="white")

    # Wird vom Mausklick getriggert
    def _on_resume_click(self):
        if self.match_controller.is_paused:
            EventBus.emit("CMD_TOGGLE_PAUSE")

    def _ui_on_timer_tick(self, data):
        time_str = self.match_controller.format_time(data.get("time_left"))
        self.ux_service.update_during_turn(time_str, data.get("time_left"), data.get("is_paused"))

    def _ui_on_time_up(self):
        if not self._is_time_up:
            self._is_time_up = True
            self.btn_pause.configure(state="disabled")
            self.status_label.configure(text="Hände weg! Auto-Save wird durchgeführt...", text_color="orange")
            EventBus.emit("UX_SHOW_WARNING", data={"text": "Auto-Save!"})
            EventBus.emit("CMD_FORCE_AUTO_SAVE")

    def _ui_on_game_over(self):
        EventBus.emit("UX_END_TURN")
        EventBus.emit("CMD_STOP_DAW_MONITOR")
        EventBus.emit("CMD_STOP_SYNC_MONITOR")
        self.status_label.configure(text="Spiel beendet! Lade Finish-Screen...", text_color="#1DB954")

    def leave_game(self):
        EventBus.emit("UX_END_TURN")
        EventBus.emit("CMD_STOP_DAW_MONITOR")
        EventBus.emit("CMD_STOP_SYNC_MONITOR")
        self.network.disconnect()
        if self.router: self.router.show_home()

    def _auto_start_my_turn(self):
        next_player = self.game_state.get_next_active_player(self.match_controller.last_finished_player)

        if not next_player:
            self.match_controller._check_game_over()
            return

        if next_player == self.game_state.my_name:
            self.status_label.configure(text="Öffne DAW...", text_color="yellow")

            actual_template = get_template_path(self.game_state.selected_template_path)

            EventBus.emit("CMD_LAUNCH_DAW", data={
                "project_path": self.game_state.local_project_path,
                "template_path": actual_template
            })
        else:
            self.status_label.configure(text=f"Download fertig! Warte auf {next_player}...", text_color="gray")

    def _on_daw_started(self):
        EventBus.emit("UX_START_TURN")
        self.status_label.configure(text="Timer startet beim nächsten Klick!", text_color="yellow")
        EventBus.emit("UX_SHOW_WARNING", data={"text": "Warten auf Klick..."})
        EventBus.emit("CMD_WAIT_DAW_INTERACTION")

    def _start_my_timer_ui(self):
        EventBus.emit("CMD_START_LOCAL_TURN")
        self.btn_pause.configure(state="normal")
        self._is_time_up = False
        EventBus.emit("CMD_WAIT_DAW_EXIT")

    def _process_turn_end(self):
        if self.game_state.active_player != self.game_state.my_name: return

        # FIX (Timer Asynchronität): Wir löschen den aktiven Spieler LOKAL sofort
        self.game_state.active_player = None

        EventBus.emit("UX_END_TURN")
        self.btn_pause.configure(state="disabled")

        time_left = self.game_state.times.get(self.game_state.my_name, 0)
        self.status_label.configure(text="Speichere Projekt... Bitte warten.", text_color="yellow")
        self.network.send_signal("PREPARE_SYNC", data={"remaining_time": time_left})

        EventBus.emit("CMD_WAIT_FOR_LOCK", data={"max_attempts": 100})

    def _on_sync_lock_timeout(self):
        self.status_label.configure(text="Fehler beim Lesen der Datei!", text_color="red")

        # ABSOLUT KUGELSICHER: Wenn self._is_time_up True ist, ignorieren wir jegliche Float-Werte!
        is_eliminated = self._is_time_up or (self.game_state.times.get(self.game_state.my_name, 0) <= 0)

        EventBus.emit("CMD_END_TURN_ELIMINATED" if is_eliminated else "CMD_END_TURN_SUCCESS", data={"file_hash": None})

    def _on_sync_lock_released(self, data):
        self.status_label.configure(text="Prüfsumme berechnet...", text_color="yellow")

        # ABSOLUT KUGELSICHER: Wenn self._is_time_up True ist, ignorieren wir jegliche Float-Werte!
        is_eliminated = self._is_time_up or (self.game_state.times.get(self.game_state.my_name, 0) <= 0)

        EventBus.emit("CMD_END_TURN_ELIMINATED" if is_eliminated else "CMD_END_TURN_SUCCESS",
                      data={"file_hash": data.get("hash")})

    def _start_download_watcher(self, data):
        if not data.get("expected_to_sync"):
            self.status_label.configure(text=f"{data.get('last_player')} hat aufgegeben. Überspringe Download...",
                                        text_color="orange")
            self.after(2000, self._auto_start_my_turn)
            return

        self.status_label.configure(text=f"{data.get('last_player')} ist fertig. Lade Projekt herunter...",
                                    text_color="yellow")
        EventBus.emit("CMD_WATCH_DOWNLOAD", data={"expected_hash": data.get("expected_hash")})

    def _on_download_finished(self, data):
        if data.get("success"):
            self._auto_start_my_turn()
        else:
            self.status_label.configure(text="Download Timeout! Starte trotzdem...", text_color="red")
            self.after(2000, self._auto_start_my_turn)

    def update_ui_text(self):
        for player in self.game_state.players:
            time_left = self.game_state.times.get(player, 0)
            bonus_str = self.game_state.bonus_texts.get(player, "")
            if player in self.player_labels:
                label = self.player_labels[player]
                if player in self.game_state.eliminated_players:
                    label.configure(text=f"❌ {player}: {self.match_controller.format_time(time_left)}",
                                    text_color="#c0392b")
                elif player == self.game_state.active_player:
                    color = "#1DB954" if player == self.game_state.my_name else "white"
                    if self.match_controller.is_paused: color = "#e67e22"
                    label.configure(text=f"▶ {player}: {self.match_controller.format_time(time_left)}{bonus_str} ◀",
                                    text_color=color)
                else:
                    label.configure(text=f"   {player}: {self.match_controller.format_time(time_left)}{bonus_str}",
                                    text_color="gray")