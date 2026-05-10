# ================================================
# FILE: services/ux_service.py
# ================================================
import logging
from pynput import keyboard
from ui.components.mini_player import MiniPlayer
from ui.components.toast import ToastNotification
from core.event_bus import EventBus
from core.i18n import translate


class UXService:
    def __init__(self, ui_mode, root_window, game_state_ref):
        self.ui_mode = ui_mode
        self.root_window = root_window
        self.game_state_ref = game_state_ref

        self.mini_player = None
        self.countdown_toast = None
        self.hotkey_listener = None
        self._notified_milestones = set()

        logging.info(f"[UXService] Gestartet im Modus: {self.ui_mode}")

        self._listeners = {
            "UX_START_TURN": lambda d: self.root_window.after(0, self.start_turn),
            "UX_END_TURN": lambda d: self.root_window.after(0, self.end_turn),
            "UX_SHOW_WARNING": lambda d: self.root_window.after(0, lambda: self.show_warning(d.get("text"))),
            "STATE_TIMER_TICK": lambda d: self.root_window.after(0, lambda: self.update_during_turn(d.get("time_str"),
                                                                                                    d.get("time_left"),
                                                                                                    d.get(
                                                                                                        "is_paused"))),
            "STATE_PAUSED": lambda d: self.root_window.after(0, lambda: self._on_pause_event(True, d.get("player"))),
            "STATE_RESUMED": lambda d: self.root_window.after(0, lambda: self._on_pause_event(False, d.get("player")))
        }
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def cleanup(self):
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)
        self.root_window.after(0, self.end_turn)

    def _on_pause_event(self, is_paused, player_name):
        if self.ui_mode == "Stealth" and player_name == self.game_state_ref.my_name:
            if is_paused:
                ToastNotification(self.root_window, translate("ux.paused"), color="#e67e22")
            else:
                ToastNotification(self.root_window, translate("ux.resumed"), color="#1DB954")

    def start_turn(self):
        self._notified_milestones.clear()
        if self.ui_mode == "Mini-Player":
            if not self.mini_player:
                self.mini_player = MiniPlayer(self.root_window)
        elif self.ui_mode == "Stealth":
            ToastNotification(self.root_window, translate("ux.daw_running"))
            self.hotkey_listener = keyboard.GlobalHotKeys({'<ctrl>+<shift>+p': self._stealth_pause_hotkey})
            self.hotkey_listener.start()

    def end_turn(self):
        if self.mini_player:
            self.mini_player.destroy()
            self.mini_player = None
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        if self.countdown_toast and self.countdown_toast.winfo_exists():
            self.countdown_toast.destroy()
            self.countdown_toast = None

    def update_during_turn(self, time_str, time_left, is_paused):
        if self.mini_player:
            self.mini_player.update_display(time_str, is_paused)
        if self.ui_mode == "Stealth" and not is_paused:
            self._handle_stealth_countdown(time_left)

    def show_warning(self, text):
        if self.mini_player:
            self.mini_player.update_status(text, is_warning=True)

    def _stealth_pause_hotkey(self):
        logging.debug("[UXService] Stealth Pause Hotkey gedrückt!")
        self.root_window.after(0, lambda: EventBus.emit("CMD_TOGGLE_PAUSE"))

    def _handle_stealth_countdown(self, time_left):
        sec_left = int(time_left)
        if sec_left in [300, 60] and sec_left not in self._notified_milestones:
            self._notified_milestones.add(sec_left)
            mins = sec_left // 60
            secs = sec_left % 60
            msg = translate("ux.time_left_min_sec").format(mins=mins, secs=f"{secs:02d}")
            ToastNotification(self.root_window, msg, color="#e67e22")

        if 0 < sec_left <= 10:
            msg = translate("ux.time_left_sec").format(secs=sec_left)
            if sec_left not in self._notified_milestones:
                self._notified_milestones.add(sec_left)
                if self.countdown_toast and self.countdown_toast.winfo_exists():
                    self.countdown_toast.update_text(msg)
                else:
                    self.countdown_toast = ToastNotification(self.root_window, msg, color="#c0392b", duration=12000)
        elif sec_left <= 0:
            if self.countdown_toast and self.countdown_toast.winfo_exists():
                self.countdown_toast.destroy()
                self.countdown_toast = None