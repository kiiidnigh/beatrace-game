# ================================================
# FILE: tests/test_event_bus.py
# ================================================
from core.event_bus import EventBus


def test_event_bus_distinct_blocks_spam(event_catcher):
    """
    Testet das Spam-Protection-Feature des EventBus.
    Sichert ab, dass Background-Loops die UI nicht überfluten.
    """
    # 1. Aktion: Identisches Event wird 3x schnell hintereinander gefeuert
    EventBus.emit_distinct("SYS_TEST_SPAM", {"status": "LOCKED"})
    EventBus.emit_distinct("SYS_TEST_SPAM", {"status": "LOCKED"})
    EventBus.emit_distinct("SYS_TEST_SPAM", {"status": "LOCKED"})

    # 2. Aktion: Status ändert sich
    EventBus.emit_distinct("SYS_TEST_SPAM", {"status": "UNLOCKED"})

    # 3. Assertions (Erwartung): Das erste Event darf nur 1x durchkommen, das zweite 1x.
    assert event_catcher.fired_events.count("SYS_TEST_SPAM") == 2