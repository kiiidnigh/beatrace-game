# ================================================
# FILE: tests/test_integration.py
# ================================================
from core.event_bus import EventBus
from core.events import SysEvents
from services.system_monitor_service import SystemMonitorService
import time


def test_system_monitor_blocks_fl_start(event_catcher, dummy_daw):
    """
    Testet das Law of Demeter und OCP:
    Wirft der SystemMonitor das richtige Event, wenn jemand versucht FL Studio manuell zu öffnen?
    """
    monitor = SystemMonitorService()
    monitor.daw = dummy_daw
    monitor.state = "LOCKED"  # Wir simulieren, dass wir in der Lobby sind

    monitor.start()
    time.sleep(0.5)
    monitor.stop()

    # Da die Fake-DAW nicht lief, sollte kill_all_instances False zurückgegeben haben.
    # Es durfte also KEIN Block-Event gefeuert werden!
    assert SysEvents.FL_MANUAL_START_BLOCKED not in event_catcher.fired_events


def test_system_monitor_detects_running_daw(event_catcher, dummy_daw):
    """Prüft, ob der Monitor die UI warnt, wenn die DAW noch vom letzten Mal offen ist."""
    monitor = SystemMonitorService()
    monitor.daw = dummy_daw
    monitor.state = "WAITING_FOR_CLOSE"

    # Wir simulieren: Der Nutzer hat FL Studio noch offen!
    dummy_daw._is_running = True

    monitor.start()
    time.sleep(0.6)
    monitor.stop()

    # Der Event-Spion muss mitgehört haben, dass das Warn-Event gefeuert wurde
    assert SysEvents.FL_WARNING_SHOW in event_catcher.fired_events