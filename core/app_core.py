# ================================================
# FILE: core/app_core.py
# ================================================
import logging
from core.game_state import GameState
from network.mqtt_client import NetworkManager
from services.system_monitor_service import SystemMonitorService
from services.discord_service import DiscordService
from services.presence_service import PresenceService
from services.updater_service import UpdaterService
from services.sound_service import SoundService
from services.lobby_service import LobbyService
from services.identity_service import IdentityService
from services.friend_service import FriendService
from services.workspace_service import WorkspaceService
from services.telemetry_service import TelemetryService
from services.flp_analyzer_service import FLPAnalyzerService


class AppCore:
    """
    Der zentrale Service Locator (IoC Container).
    Verwaltet den Lebenszyklus aller Backend-Services unabhängig von der UI.
    """

    def __init__(self):
        logging.info("[AppCore] Initialisiere Kernsystem...")

        # 1. Daten-Services (Stateful, speichern Cache im RAM)
        self.identity_service = IdentityService()
        self.friend_service = FriendService()
        self.workspace_service = WorkspaceService()
        self.telemetry_service = TelemetryService()
        self.analyzer_service = FLPAnalyzerService()

        # 2. State & Netzwerk
        self.game_state = GameState(self.identity_service)
        self.network = NetworkManager()

        # 3. Hintergrund-Services booten
        self.sound_service = SoundService()
        self.system_monitor = SystemMonitorService()
        self.discord_service = DiscordService()
        self.presence_service = PresenceService(self.identity_service, self.friend_service)
        self.updater_service = UpdaterService()

        # 4. Verknüpfte Services (Dependencies injizieren)
        self.lobby_service = LobbyService(self.game_state, self.network, self.workspace_service)

    def start(self):
        """Fährt alle aktiven Hintergrund-Dienste hoch."""
        logging.info("[AppCore] Starte Hintergrund-Dienste...")
        self.system_monitor.start()
        self.presence_service.start()

    def stop(self):
        """Sicheres Beenden aller Dienste beim Schließen der App."""
        logging.info("[AppCore] Fahre System herunter...")
        self.system_monitor.stop()
        self.presence_service.stop()
        self.lobby_service.stop()

        self.discord_service.cleanup()
        self.updater_service.cleanup()
        self.sound_service.cleanup()

        self.identity_service.cleanup()
        self.friend_service.cleanup()
        self.workspace_service.cleanup()
        self.telemetry_service.cleanup()
        self.analyzer_service.cleanup()

        self.network.disconnect()