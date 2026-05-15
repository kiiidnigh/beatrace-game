# ================================================
# FILE: ui/views/game_view.py
# ================================================
import customtkinter as ctk
from utils.file_utils import load_prefs
from core.event_bus import EventBus
from core.events import StateEvents, CmdEvents, UIEvents, SysEvents, NetEvents
from core.match_manager import MatchManager
from services.ux_service import UXService
from core.i18n import translate
from ui.components.custom_popup import CustomPopup
from ui.views.base_view import BaseView


class GameView(BaseView):
    def __init__(self, master, game_state, network, router=None, **kwargs):
        super().__init__(master, **kwargs)
        self.game_state = game_state
        self.network = network
        self.router = router
        self.player_labels = {}

        ui_mode = load_prefs().get("ui_mode", "Standard")
        self.ux_service = UXService(ui_mode, self.winfo_toplevel(), self.game_state)
        self.match_manager = MatchManager(self.game_state, self.network, self.router)

        # Typisierte Events verwenden (Fail Fast!)
        self._listeners = {
            StateEvents.TURN_START: self._apply_turn_start,
            StateEvents.PAUSED: self._apply_pause,
            StateEvents.RESUMED: self._apply_resume,
            StateEvents.TIMER_TICK: self._apply_timer_tick,
            StateEvents.TIME_UP: self._apply_time_up,
            StateEvents.GAME_OVER: self._apply_game_over,
            StateEvents.TURN_END: self._apply_turn_end,
            StateEvents.ELIMINATED: self._apply_eliminated,
            UIEvents.STATUS_UPDATE: lambda d: self.status_label.configure(text=d.get("text"), text_color=d.get("color", "white")),
            "DAW_RESUME_CLICK_DETECTED": self._apply_resume_click,  # (Beispielhaft als String gelassen, falls noch nicht ausgelagert, aber idealerweise auch ins Dictionary aufnehmen!)
            UIEvents.LANGUAGE_CHANGED: self.update_texts,
            NetEvents.LOBBY_CLOSED: self._on_host_closed_match
        }
        self.register_listeners()

        self.setup_ui()
        self._ui_tick()
        self.match_manager.start_match()

        if not self.game_state.is_host and self.game_state.players:
            msg = translate("game.status_started_other").format(player=self.game_state.players[0])
            self.status_label.configure(text=msg, text_color="white")

    def destroy(self):
        self.match_manager.cleanup()
        super().destroy()

    def update_texts(self, data=None):
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

        self.control_frame = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.control_frame.pack_propagate(False)
        self.control_frame.pack(fill="x", side="bottom", pady=(10, 30))

        self.btn_pause = ctk.CTkButton(self.control_frame, text=translate("game.btn_pause"), width=250, height=50,
                                       font=("Helvetica", 16, "bold"),
                                       command=lambda: EventBus.emit(CmdEvents.TOGGLE_PAUSE))
        self.btn_pause.pack_forget()

    def _ui_tick(self):
        if getattr(self, '_is_destroyed', False) or not self.winfo_exists():
            return
        EventBus.emit(SysEvents.TICK)
        self.update_ui_text()
        self.after(100, self._ui_tick)

    def _apply_turn_start(self, data):
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

    def _apply_pause(self, data):
        player = data.get("player")
        if player == self.game_state.my_name:
            msg = translate("game.btn_resume").format(penalty=self.game_state.penalty_seconds)
            self.btn_pause.configure(text=msg, fg_color="#e67e22", state="disabled")
            self.after(500, lambda: EventBus.emit(CmdEvents.WAIT_RESUME_CLICK))
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

    def _apply_resume_click(self, data=None):
        if self.match_manager.match_controller.is_paused:
            EventBus.emit(CmdEvents.TOGGLE_PAUSE)

    def _apply_timer_tick(self, data):
        time_str = self.match_manager.match_controller.format_time(data.get("time_left"))
        self.ux_service.update_during_turn(time_str, data.get("time_left"), data.get("is_paused"))

    def _apply_time_up(self, data=None):
        self.btn_pause.configure(state="disabled")

    def _apply_game_over(self, data=None):
        EventBus.emit(UIEvents.UX_END_TURN)
        if self.btn_pause.winfo_ismapped():
            self.btn_pause.pack_forget()
        self.status_label.configure(text=translate("game.status_game_over"), text_color="#1DB954")

    def _apply_turn_end(self, data):
        if data.get("player") == self.game_state.my_name:
            self.status_label.configure(text=translate("game.status_turn_ended"), text_color="orange")

    def _apply_eliminated(self, data):
        if data.get("player") == self.game_state.my_name:
            self.status_label.configure(text=translate("game.status_eliminated"), text_color="red")

    def _on_host_closed_match(self, data=None):
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
        EventBus.emit(UIEvents.UX_END_TURN)
        if self.game_state.is_host:
            self.network.send_signal("LOBBY_CLOSED")
        else:
            self.network.send_signal("CLIENT_LEAVE")

        self.network.disconnect()
        if self.router: self.router.show_home()

    def update_ui_text(self):
        for player, label in self.player_labels.items():
            time_left = self.game_state.get_player_time(player)
            bonus_str = self.game_state.get_bonus_text(player)

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