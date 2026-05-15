# ================================================
# FILE: services/sound_service.py
# ================================================
import os
import logging
import customtkinter as ctk
from core.event_bus import EventBus
from utils.file_utils import load_prefs
from config import settings
from services.base_service import BaseService

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logging.warning("[SoundService] Pygame-CE nicht installiert. Sounds deaktiviert.")


class SoundService(BaseService):
    def __init__(self):
        super().__init__()
        self.sounds = {}
        self.last_tick_step = -1

        self._reload_settings()

        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
                pygame.mixer.init()

                self._load_sounds()
                self._monkeypatch_ctk_buttons()
            except Exception as e:
                logging.error(f"[SoundService] Fehler bei Pygame Init: {e}")

        self._listeners = {
            "NET_CLIENT_JOIN": lambda d: self.play("lobby_join"),
            "NET_CLIENT_LEAVE": lambda d: self.play("lobby_leave"),
            "STATE_MATCH_STARTED": lambda d: self.play("match_start"),
            "STATE_TIMER_TICK": self._on_tick,
            "STATE_TURN_END": lambda d: self.play("turn_end"),
            "STATE_ELIMINATED": lambda d: self.play("eliminated"),
            "STATE_FINISHED": lambda d: self.play("match_finish"),
            "STATE_GAME_OVER": lambda d: self.play("match_finish"),
            "SETTINGS_UPDATED": self._reload_settings
        }
        self.register_listeners()

    def _monkeypatch_ctk_buttons(self):
        original_clicked = ctk.CTkButton._clicked
        service_ref = self

        def new_clicked(self_btn, event=None):
            service_ref.play("btn_click")
            return original_clicked(self_btn, event)

        ctk.CTkButton._clicked = new_clicked

    def _load_sounds(self):
        base_dir = os.path.join(settings.BASE_DIR, "assets", "sounds")
        sound_files = {
            "btn_click": "click.wav",
            "lobby_join": "join.wav",
            "lobby_leave": "leave.wav",
            "match_start": "start.wav",
            "tick_1": "tick_1.wav",
            "tick_2": "tick_2.wav",
            "tick_3": "tick_3.wav",
            "turn_end": "turn_end.wav",
            "eliminated": "eliminated.wav",
            "match_finish": "finish.wav"
        }

        sounds_loaded = 0
        for key, filename in sound_files.items():
            path = os.path.join(base_dir, filename)
            if os.path.exists(path):
                try:
                    self.sounds[key] = pygame.mixer.Sound(path)
                    sounds_loaded += 1
                except Exception as e:
                    logging.error(f"[SoundService] Konnte Sound {filename} nicht laden: {e}")
            else:
                logging.debug(f"[SoundService] Sounddatei fehlt: {path}")

        logging.info(f"[SoundService] {sounds_loaded} Sounds erfolgreich geladen.")

    def _reload_settings(self, data=None):
        self.prefs = load_prefs().get("sounds", {})
        self.master_volume = self.prefs.get("master_volume", 80) / 100.0

    def play(self, sound_key):
        if not PYGAME_AVAILABLE: return

        pref_key = "tick" if sound_key.startswith("tick") else sound_key
        if not self.prefs.get(pref_key, True): return

        if sound_key in self.sounds:
            sound = self.sounds[sound_key]
            sound.set_volume(self.master_volume)
            sound.play()

    def _on_tick(self, data):
        time_left = data.get("time_left", 0)

        if time_left <= 0:
            return

        if time_left <= 3.0:
            interval = 0.25
            tick_sound = "tick_3"
        elif time_left <= 6.0:
            interval = 0.5
            tick_sound = "tick_2"
        elif time_left <= 10.0:
            interval = 1.0
            tick_sound = "tick_1"
        else:
            return

        current_step = int(time_left / interval)
        if current_step != self.last_tick_step:
            self.last_tick_step = current_step
            self.play(tick_sound)