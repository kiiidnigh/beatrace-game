# ================================================
# FILE: ui/views/game_view.py
# ================================================
import customtkinter as ctk
from utils.file_utils import load_prefs
from core.event_bus import EventBus
from core.match_manager import MatchManager
from services.ux_service import UXService
from core.i18n import translate
from ui.components.custom_popup import CustomPopup


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
            "STATE_TURN_END": lambda d: self.safe_execute(self._apply_turn_end, d),
            "STATE_ELIMINATED": lambda d: self.safe_execute(self._apply_eliminated, d),
            "UI_STATUS_UPDATE": lambda d: self.safe_execute(
                lambda: self.status_label.configure(text=d.get("text"), text_color=d.get("color", "white"))),
            "DAW_RESUME_CLICK_DETECTED": lambda d: self.safe_execute(self._apply_resume_click),
            "LANGUAGE_CHANGED": lambda d: self.safe_execute(self.update_texts),
            "NET_LOBBY_CLOSED": lambda d: self.safe_execute(self._on_host_closed_match)
        }
        self._setup_event_listeners()
        self.setup_ui()

        self._ui_tick()
        self.match_manager.start_match()

        if not self.game_state.is_host and self.game_state.players:
            msg = translate("game.status_started_other").format(player=self.game_state.players[0])
            self.status_label.configure(text=msg, text_color="white")

    def safe_execute(self, func, *args):
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
        self._is_destroyed = True
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)
        self.match_manager.cleanup()
        self.pack_forget()
        self.after(100, lambda: ctk.CTkFrame.destroy(self))

    def update_texts(self):
        self.lbl_title.configure(text=translate("game.title"))
        self.btn_leave.configure(text=translate("common.btn_leave"))
        if self.btn_pause.winfo_ismapped() and "PAUSE" in self.btn_pause.cget("text"):
            self.btn_pause.configure(text=translate("game.btn_pause"))

    def setup_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.lbl_title = ctk.CTkLabel(header_frame, text=translate("game.title"), font=("Helvetica", 24, "bold"))
        self.lbl_title.pack(side="left")

        self.btn_leave = ctk.CTkButton(header_frame, text=translate("common.btn_leave"), width=100, height=40,
                                       font=("Helvetica", 14),
                                       fg_color="#c0392b", hover_color="#e74c3c", command=self.leave_game)
        self.btn_leave.pack(side="right")

        self.status_label = ctk.CTkLabel(self, text=translate("common.initializing"), text_color="gray",
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

        # Eine feste Höhe für den Control-Frame verhindert, dass das Layout springt, wenn der Button verschwindet
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.control_frame.pack_propagate(False)
        self.control_frame.pack(fill="x", side="bottom", pady=(10, 30))

        self.btn_pause = ctk.CTkButton(self.control_frame, text=translate("game.btn_pause"), width=250, height=50,
                                       font=("Helvetica", 16, "bold"),
                                       command=lambda: EventBus.emit("CMD_TOGGLE_PAUSE"))

        # Startet initial versteckt
        self.btn_pause.pack_forget()

    def _ui_tick(self):
        if getattr(self, '_is_destroyed', False) or not self.winfo_exists():
            return
        EventBus.emit("SYS_TICK")
        self.update_ui_text()
        self.after(100, self._ui_tick)

    def _apply_turn_start(self, data):
        player = data.get("player")

        if player == self.game_state.my_name:
            self.btn_pause.configure(state="normal", text=translate("game.btn_pause"), fg_color=["#3a7ebf", "#1f538d"])
            # Button einblenden, wenn wir am Zug sind
            if not self.btn_pause.winfo_ismapped():
                self.btn_pause.pack(expand=True)
            self.status_label.configure(text=translate("game.status_your_turn"), text_color="#1DB954")
        else:
            # Button verstecken, wenn die anderen am Zug sind
            if self.btn_pause.winfo_ismapped():
                self.btn_pause.pack_forget()
            self.status_label.configure(text=translate("game.status_other_turn").format(player=player),
                                        text_color="white")

    def _apply_pause(self, data):
        player = data.get("player")
        if player == self.game_state.my_name:
            msg = translate("game.btn_resume").format(penalty=self.game_state.penalty_seconds)
            self.btn_pause.configure(text=msg, fg_color="#e67e22", state="disabled")
            self.after(500, lambda: EventBus.emit("CMD_WAIT_RESUME_CLICK"))
        self.status_label.configure(text=translate("game.status_paused"), text_color="#e67e22")

    def _apply_resume(self, data):
        player = data.get("player")
        if player == self.game_state.my_name:
            self.btn_pause.configure(state="normal", text=translate("game.btn_pause"), fg_color=["#3a7ebf", "#1f538d"])
            if not self.btn_pause.winfo_ismapped():
                self.btn_pause.pack(expand=True)
            self.status_label.configure(text=translate("game.status_your_turn"), text_color="#1DB954")
        else:
            if self.btn_pause.winfo_ismapped():
                self.btn_pause.pack_forget()
            self.status_label.configure(text=translate("game.status_other_turn").format(player=player),
                                        text_color="white")

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
        if self.btn_pause.winfo_ismapped():
            self.btn_pause.pack_forget()
        self.status_label.configure(text=translate("game.status_game_over"), text_color="#1DB954")

    def _apply_turn_end(self, data):
        # FIX: Nur den lokalen Status umschalten, wenn wir selbst abgegeben haben
        if data.get("player") == self.game_state.my_name:
            self.status_label.configure(text=translate("game.status_turn_ended"), text_color="orange")

    def _apply_eliminated(self, data):
        # FIX: Nur den lokalen Status umschalten, wenn wir selbst ausgeschieden sind
        if data.get("player") == self.game_state.my_name:
            self.status_label.configure(text=translate("game.status_eliminated"), text_color="red")

    def _on_host_closed_match(self):
        """Wenn der Host mitten im Game das Spiel verlässt, kicken wir den Client sicher raus."""
        self.network.disconnect()
        self.game_state.reset_match_data()

        def on_close():
            if self.router: self.router.show_home()

        CustomPopup(
            master=self.winfo_toplevel(),
            title=translate("lobby.closed_title"),
            message=translate("lobby.closed_msg"),
            icon="ℹ️",
            btn_color="#3a7ebf",
            sound_type="info",
            on_confirm_callback=on_close,
            on_cancel_callback=on_close
        )

    def leave_game(self):
        EventBus.emit("UX_END_TURN")

        if self.game_state.is_host:
            self.network.send_signal("LOBBY_CLOSED")
        else:
            self.network.send_signal("CLIENT_LEAVE")

        self.network.disconnect()
        if self.router: self.router.show_home()

    def update_ui_text(self):
        # FIX: Wir iterieren über die Labels, NICHT über game_state.players,
        # da der MatchController den Spieler aus der Liste löscht, wenn er verlässt.
        for player, label in self.player_labels.items():
            time_left = self.game_state.get_player_time(player)
            bonus_str = self.game_state.get_bonus_text(player)

            # Spieler wurde eliminiert ODER hat das Spiel komplett verlassen
            if player in self.game_state.eliminated_players or player not in self.game_state.players:
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