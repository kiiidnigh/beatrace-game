# ================================================
# FILE: services/base_service.py
# ================================================
from core.event_bus import EventBus

class BaseService:
    """
    Basis-Klasse für alle Services.
    Übernimmt automatisch das An- und Abmelden beim EventBus.
    """
    def __init__(self):
        if not hasattr(self, '_listeners'):
            self._listeners = {}

    def register_listeners(self):
        """Wird von Kindklassen aufgerufen, nachdem _listeners befüllt wurde."""
        for event, func in self._listeners.items():
            EventBus.subscribe(event, func)

    def cleanup(self):
        """Standard-Cleanup. Kindklassen können das überschreiben (super().cleanup() aufrufen!)."""
        for event, func in self._listeners.items():
            EventBus.unsubscribe(event, func)