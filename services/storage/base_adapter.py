# ================================================
# FILE: services/storage/base_adapter.py
# ================================================
from abc import ABC, abstractmethod

class SyncException(Exception):
    """
    Spezifische Exception für Cloud- und Dateisystem-Fehler (Fail Fast).
    Wird vom EventBus gefangen und an die UI (UIController) weitergeleitet.
    """
    pass


class BaseStorageAdapter(ABC):
    """
    Interface für alle Storage-Provider.
    Garantiert das OCP (Open/Closed Principle) für den SyncService.
    """

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Prüft, ob der Storage-Adapter bereit und autorisiert ist."""
        pass

    @abstractmethod
    def authenticate(self):
        """Führt den Login/Auth-Flow aus (z.B. öffnet den Browser für OAuth)."""
        pass

    @abstractmethod
    def upload(self, local_path: str, remote_path: str):
        """Lädt eine lokale Datei hoch. Wirft SyncException bei Fehlern."""
        pass

    @abstractmethod
    def download(self, remote_path: str, local_path: str):
        """Lädt eine Datei herunter. Wirft SyncException bei Fehlern."""
        pass