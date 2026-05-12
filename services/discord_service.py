# ================================================
# FILE: services/discord_service.py
# ================================================
import time
import logging
import threading
from pypresence import Presence
from core.event_bus import EventBus
from config.settings import DISCORD_APP_ID

class DiscordService:


    def __init__(self):
        self.rpc = None
        self._is_connected = False
        self._current_state = "Idle"
        self._current_details = "In Menus"

        self._listeners = {
            "STATE_MATCH_STARTED": lambda d: self.update_presence("In Game", "Producing a Beat"),
            "STATE_GAME_OVER": lambda d: self.update_presence("Finished", "Reviewing Project"),
            "NET_CONNECTED": lambda d: self.update_presence("In Lobby", "Waiting for Players"),
            "NET_LOBBY_CLOSED": lambda d: self.update_presence("In Menus", "Idle")
        }

        # Startet die Verbindung in einem eigenen Thread, um UI-Blocking zu vermeiden
        threading.Thread(target=self._connect, daemon=True).start()
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def _connect(self):
        try:
            self.rpc = Presence(DISCORD_APP_ID)
            self.rpc.connect()
            self._is_connected = True
            logging.info("[DiscordService] Rich Presence erfolgreich verbunden.")
            self.update_presence(self._current_state, self._current_details)
        except Exception as e:
            logging.warning(f"[DiscordService] Discord nicht gefunden oder Fehler: {e}")
            self._is_connected = False

    def update_presence(self, state, details, party_size=None, party_max=None):
        if not self._is_connected or not self.rpc:
            return

        self._current_state = state
        self._current_details = details

        try:
            self.rpc.update(
                state=state,
                details=details,
                large_image="logo_large",  # Muss im Discord Developer Portal hochgeladen werden
                large_text="Beatrace Game",
                start=time.time() if state == "In Game" else None,
                party_id="beatrace_session" if party_size else None,
                party_size=[party_size, party_max] if party_size else None
            )
        except Exception as e:
            logging.error(f"[DiscordService] Update fehlgeschlagen: {e}")

    def cleanup(self):
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)
        if self.rpc:
            try:
                self.rpc.close()
            except:
                pass