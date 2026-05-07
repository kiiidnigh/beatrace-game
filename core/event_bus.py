import logging
import threading


class EventBus:
    _listeners = {}
    _lock = threading.Lock()

    # NEU: Speichert den letzten Zustand für Events, um Spam zu verhindern
    _last_emitted_state = {}

    @classmethod
    def subscribe(cls, event_type, listener_func):
        with cls._lock:
            if event_type not in cls._listeners:
                cls._listeners[event_type] = []

            # Verhindert, dass dieselbe Funktion mehrmals dasselbe Event abonniert
            if listener_func not in cls._listeners[event_type]:
                cls._listeners[event_type].append(listener_func)
                logging.debug(f"[EventBus] '{listener_func.__name__}' hat '{event_type}' abonniert.")

    @classmethod
    def unsubscribe(cls, event_type, listener_func):
        with cls._lock:
            if event_type in cls._listeners and listener_func in cls._listeners[event_type]:
                cls._listeners[event_type].remove(listener_func)
                logging.debug(f"[EventBus] '{listener_func.__name__}' hat '{event_type}' deabonniert.")

    @classmethod
    def emit(cls, event_type, data=None):
        if data is None:
            data = {}

        logging.info(f"[EventBus] EMIT: {event_type}")

        # Wir kopieren die Listener-Liste innerhalb des Locks
        with cls._lock:
            if event_type in cls._listeners:
                listeners_copy = list(cls._listeners[event_type])
            else:
                listeners_copy = []

        for listener in listeners_copy:
            try:
                listener(data)
            except Exception as e:
                logging.error(
                    f"[EventBus] Kritischer Fehler im Listener '{listener.__name__}' fuer Event '{event_type}': {e}",
                    exc_info=True
                )

    @classmethod
    def emit_distinct(cls, event_type, data=None):
        """
        Feuert ein Event NUR ab, wenn es sich vom letzten Aufruf unterscheidet.
        Perfekt, um Log-Spam durch Endlosschleifen (wie Monitore) zu verhindern!
        """
        if data is None:
            data = {}

        with cls._lock:
            last_data = cls._last_emitted_state.get(event_type)

            # Wenn das Event schonmal gefeuert wurde und die Daten exakt gleich sind: Abbruch!
            if event_type in cls._last_emitted_state and last_data == data:
                return

            # Ansonsten: Neuen Zustand speichern
            cls._last_emitted_state[event_type] = data

        # Normales emit aufrufen (außerhalb des Locks)
        cls.emit(event_type, data)

    @classmethod
    def clear_history(cls):
        """Löscht die Spam-Historie (z.B. bei Statuswechseln im System)."""
        with cls._lock:
            cls._last_emitted_state.clear()