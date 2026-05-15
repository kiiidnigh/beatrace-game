# ================================================
# FILE: tests/test_app_core.py
# ================================================
from core.app_core import AppCore


def test_app_core_boot_and_shutdown():
    """
    Testet den gesamten Lebenszyklus des IoC-Containers.
    Dank der isolierten APPDATA-Fixture zerschießen wir hier keine echten Configs.
    """
    # 1. Aktion: App-Gehirn instanziieren
    core = AppCore()

    # 2. Aktion: Hintergrund-Dienste starten
    core.start()

    # Assertions: Die wichtigsten Services müssen hochgefahren sein
    assert core.system_monitor._running is True
    assert core.presence_service.is_running is True

    # 3. Aktion: App beenden
    core.stop()

    # Assertions: Alles muss sich sauber beendet haben (Keine Memory Leaks!)
    assert core.system_monitor._running is False
    assert core.presence_service.is_running is False