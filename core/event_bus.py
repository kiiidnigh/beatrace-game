import logging

class EventBus:
    _listeners = {}

    @classmethod
    def subscribe(cls, event_type, listener_func):
        if event_type not in cls._listeners:
            cls._listeners[event_type] = []
        cls._listeners[event_type].append(listener_func)
        logging.debug(f"[EventBus] '{listener_func.__name__}' hat '{event_type}' abonniert.")

    @classmethod
    def emit(cls, event_type, data=None):
        if data is None:
            data = {}

        logging.info(f"[EventBus] EMIT: {event_type}")

        if event_type in cls._listeners:
            # list() Kopie ist extrem wichtig, falls sich Listener waehrenddessen loeschen!
            for listener in list(cls._listeners[event_type]):
                try:
                    listener(data)
                except Exception as e:
                    logging.error(f"[EventBus] Kritischer Fehler im Listener '{listener.__name__}' fuer Event '{event_type}': {e}", exc_info=True)

    @classmethod
    def clear_all(cls):
        """WICHTIG: Loescht alle Geister-Verbindungen alter Lobbys/Spiele!"""
        cls._listeners.clear()
        logging.info("[EventBus] Alle Listener wurden geloescht (Clean State erreicht).")