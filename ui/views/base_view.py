# ================================================
# FILE: ui/views/base_view.py
# ================================================
import customtkinter as ctk
from core.event_bus import EventBus


class BaseView(ctk.CTkFrame):
    """
    Basis-Klasse für alle UI-Views.
    Handhabt sauberes Thread-übergreifendes Abonnieren (subscribe_ui) und Event-Cleanup.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._is_destroyed = False

        if not hasattr(self, '_listeners'):
            self._listeners = {}

    def register_listeners(self):
        """Muss von der Kindklasse aufgerufen werden, wenn self._listeners befüllt ist."""
        for event, func in self._listeners.items():
            # NEU: Nutzt automatisch die neue UI-Safe Methode des EventBus
            EventBus.subscribe_ui(self, event, func)

    def destroy(self):
        """Räumt Event-Listener auf und zerstört die UI sicher."""
        self._is_destroyed = True

        for event, func in self._listeners.items():
            EventBus.unsubscribe_ui(event, func)

        self.pack_forget()
        self.after(100, lambda: super(BaseView, self).destroy())