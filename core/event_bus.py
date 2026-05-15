# ================================================
# FILE: core/event_bus.py
# ================================================
import logging
import threading
import inspect


class EventBus:
    _listeners = {}
    _lock = threading.Lock()
    _last_emitted_state = {}
    _ui_wrappers = {}

    @classmethod
    def subscribe(cls, event_type, listener_func):
        with cls._lock:
            if event_type not in cls._listeners:
                cls._listeners[event_type] = []

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
    def subscribe_ui(cls, view_master, event_type, listener_func):
        """
        Neu: Abonnieren speziell für UI-Elemente.
        Macht den Thread-Wechsel (tkinter.after) und die Existenzprüfung automatisch.
        """
        try:
            # Prüfen, ob die Ziel-Funktion Argumente (data) erwartet
            sig = inspect.signature(listener_func)
            accepts_data = len(sig.parameters) > 0
        except ValueError:
            accepts_data = True

        def safe_wrapper(data):
            # Prüfen, ob das Fenster noch existiert, bevor wir an die UI senden
            if not getattr(view_master, '_is_destroyed', False) and view_master.winfo_exists():
                if accepts_data:
                    view_master.after(0, lambda d=data: listener_func(d))
                else:
                    view_master.after(0, listener_func)

        with cls._lock:
            cls._ui_wrappers[(event_type, listener_func)] = safe_wrapper

        cls.subscribe(event_type, safe_wrapper)

    @classmethod
    def unsubscribe_ui(cls, event_type, listener_func):
        """Neu: Gegenstück zu subscribe_ui"""
        with cls._lock:
            wrapper = cls._ui_wrappers.pop((event_type, listener_func), None)

        if wrapper:
            cls.unsubscribe(event_type, wrapper)
        else:
            cls.unsubscribe(event_type, listener_func)

    @classmethod
    def emit(cls, event_type, data=None):
        if data is None:
            data = {}

        logging.info(f"[EventBus] EMIT: {event_type}")

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
        if data is None:
            data = {}

        with cls._lock:
            last_data = cls._last_emitted_state.get(event_type)
            if event_type in cls._last_emitted_state and last_data == data:
                return
            cls._last_emitted_state[event_type] = data

        cls.emit(event_type, data)

    @classmethod
    def clear_history(cls):
        with cls._lock:
            cls._last_emitted_state.clear()