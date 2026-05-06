import logging
from pynput import keyboard
from ui.components.mini_player import MiniPlayer
from ui.components.toast import ToastNotification
from core.event_bus import EventBus


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
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        # Verbindet UI-Events sicher mit dem Main Thread (Tkinter-Regel)
        EventBus.subscribe("UX_START_TURN", lambda d: self.root_window.after(0, self.start_turn))
        EventBus.subscribe("UX_END_TURN", lambda d: self.root_window.after(0, self.end_turn))
        EventBus.subscribe("UX_SHOW_WARNING",
                           lambda d: self.root_window.after(0, lambda: self.show_warning(d.get("text"))))
        EventBus.subscribe("STATE_TIMER_TICK", lambda d: self.root_window.after(0, lambda: self.update_during_turn(
            d.get("time_str"), d.get("time_left"), d.get("is_paused"))))

        EventBus.subscribe("STATE_PAUSED",
                           lambda d: self.root_window.after(0, lambda: self._on_pause_event(True, d.get("player"))))
        EventBus.subscribe("STATE_RESUMED",
                           lambda d: self.root_window.after(0, lambda: self._on_pause_event(False, d.get("player"))))

    def _on_pause_event(self, is_paused, player_name):
        if self.ui_mode == "Stealth" and player_name == self.game_state_ref.my_name:
            if is_paused:
                ToastNotification("PAUSIERT!", color="#e67e22")
            else:
                ToastNotification("WEITER GEHTS!", color="#1DB954")

    def start_turn(self):
        self._notified_milestones.clear()
        if self.ui_mode == "Mini-Player":
            if not self.mini_player:
                # HIER DER FIX: Wir instanziieren den MiniPlayer ohne GameView-Referenz!
                self.mini_player = MiniPlayer(self.root_window)
        elif self.ui_mode == "Stealth":
            ToastNotification("DAW läuft! Klicke in die DAW, um zu starten.")
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
            ToastNotification(f"Noch {mins}:{secs:02d} übrig!", color="#e67e22")

        if 0 < sec_left <= 10:
            if sec_left not in self._notified_milestones:
                self._notified_milestones.add(sec_left)
                if self.countdown_toast and self.countdown_toast.winfo_exists():
                    self.countdown_toast.update_text(f"Noch {sec_left} Sekunden!")
                else:
                    self.countdown_toast = ToastNotification(f"Noch {sec_left} Sekunden!", color="#c0392b",
                                                             duration=12000)
        elif sec_left <= 0:
            if self.countdown_toast and self.countdown_toast.winfo_exists():
                self.countdown_toast.destroy()
                self.countdown_toast = None