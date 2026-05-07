import customtkinter as ctk
from utils.file_utils import load_prefs

from core.event_bus import EventBus
from core.match_manager import MatchManager
from services.ux_service import UXService


class GameView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router=None, **kwargs):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router
        self.player_labels = {}

        self._is_destroyed = False

        ui_mode = load_prefs().get("ui_mode", "Standard")
        self.ux_service = UXService(ui_mode, self.winfo_toplevel(), self.game_state)

        self.match_manager = MatchManager(self.game_state, self.network, self.router)

        self._listeners = {
            "STATE_TURN_START": lambda d: self.safe_execute(self._apply_turn_start, d),
            "STATE_PAUSED": lambda d: self.safe_execute(self._apply_pause, d),
            "STATE_RESUMED": lambda d: self.safe_execute(self._apply_resume, d),
            "STATE_TIMER_TICK": lambda d: self.safe_execute(self._apply_timer_tick, d),
            "STATE_TIME_UP": lambda d: self.safe_execute(self._apply_time_up),
            "STATE_GAME_OVER": lambda d: self.safe_execute(self._apply_game_over),
            "STATE_TURN_END": lambda d: self.safe_execute(
                lambda: self.status_label.configure(text="Zug abgegeben! Warte auf Sync...", text_color="orange")),
            "STATE_ELIMINATED": lambda d: self.safe_execute(
                lambda: self.status_label.configure(text="Ausgeschieden!", text_color="red")),
            "UI_STATUS_UPDATE": lambda d: self.safe_execute(
                lambda: self.status_label.configure(text=d.get("text"), text_color=d.get("color", "white"))),
            "DAW_RESUME_CLICK_DETECTED": lambda d: self.safe_execute(self._apply_resume_click)
        }
        self._setup_event_listeners()
        self.setup_ui()

        self._ui_tick()
        self.match_manager.start_match()

        if not self.game_state.is_host and self.game_state.players:
            self.status_label.configure(text=f"Spiel gestartet! {self.game_state.players[0]} lädt das Projekt...",
                                        text_color="white")

    def safe_execute(self, func, *args):
        """Kugelsichere Ausführung von UI-Updates im Main Thread."""

        def wrapper():
            if not self._is_destroyed and self.winfo_exists():
                try:
                    func(*args)
                except Exception:
                    pass

        self.after(0, wrapper)

    def _setup_event_listeners(self):
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def destroy(self):
        """Cleanup: Meldet die View sauber ab und stoppt alle Loops."""
        self._is_destroyed = True
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)
        self.match_manager.cleanup()

        # FIX für CustomTkinter Race-Condition:
        # Fenster für den Nutzer sofort ausblenden, aber erst 100ms später im
        # Speicher zerstören, damit laufende Zeichen-Prozesse sicher abschließen können.
        self.pack_forget()
        self.after(100, lambda: ctk.CTkFrame.destroy(self))

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
        if getattr(self, '_is_destroyed', False) or not self.winfo_exists():
            return
        EventBus.emit("SYS_TICK")
        self.update_ui_text()
        self.after(100, self._ui_tick)

    def _apply_turn_start(self, data):
        player = data.get("player")
        self.btn_pause.configure(state="normal", text="PAUSE", fg_color=["#3a7ebf", "#1f538d"])
        if player == self.game_state.my_name:
            self.status_label.configure(text="Dein Zug läuft! (Schließe DAW zum Abgeben)", text_color="#1DB954")
        else:
            self.status_label.configure(text=f"{player}'s Zug läuft...", text_color="white")

    def _apply_pause(self, data):
        player = data.get("player")
        if player == self.game_state.my_name:
            self.btn_pause.configure(text=f"KLICKE ZUM FORTSETZEN (-{self.game_state.penalty_seconds}s)",
                                     fg_color="#e67e22", state="disabled")
            self.after(500, lambda: EventBus.emit("CMD_WAIT_RESUME_CLICK"))
        self.status_label.configure(text=f"PAUSIERT", text_color="#e67e22")

    def _apply_resume(self, data):
        player = data.get("player")
        if player == self.game_state.my_name:
            self.btn_pause.configure(state="normal", text="PAUSE", fg_color=["#3a7ebf", "#1f538d"])
            self.status_label.configure(text="Dein Zug läuft!", text_color="#1DB954")
        else:
            self.status_label.configure(text=f"{player}'s Zug läuft...", text_color="white")

    def _apply_resume_click(self):
        if self.match_manager.match_controller.is_paused:
            EventBus.emit("CMD_TOGGLE_PAUSE")

    def _apply_timer_tick(self, data):
        time_str = self.match_manager.match_controller.format_time(data.get("time_left"))
        self.ux_service.update_during_turn(time_str, data.get("time_left"), data.get("is_paused"))

    def _apply_time_up(self):
        self.btn_pause.configure(state="disabled")

    def _apply_game_over(self):
        EventBus.emit("UX_END_TURN")
        self.status_label.configure(text="Spiel beendet! Lade Finish-Screen...", text_color="#1DB954")

    def leave_game(self):
        EventBus.emit("UX_END_TURN")
        self.network.disconnect()
        if self.router: self.router.show_home()

    def update_ui_text(self):
        for player in self.game_state.players:
            time_left = self.game_state.get_player_time(player)
            bonus_str = self.game_state.get_bonus_text(player)
            if player in self.player_labels:
                label = self.player_labels[player]
                if player in self.game_state.eliminated_players:
                    label.configure(text=f"❌ {player}: {self.match_manager.match_controller.format_time(time_left)}",
                                    text_color="#c0392b")
                elif player == self.game_state.active_player:
                    color = "#1DB954" if player == self.game_state.my_name else "white"
                    if self.match_manager.match_controller.is_paused: color = "#e67e22"
                    label.configure(
                        text=f"▶ {player}: {self.match_manager.match_controller.format_time(time_left)}{bonus_str} ◀",
                        text_color=color)
                else:
                    label.configure(
                        text=f"   {player}: {self.match_manager.match_controller.format_time(time_left)}{bonus_str}",
                        text_color="gray")