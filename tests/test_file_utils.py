# ================================================
# FILE: tests/test_file_utils.py
# ================================================
import os
from utils.file_utils import _safe_json_load
from core.events import SysEvents


def test_safe_json_load_valid_file(tmp_path, event_catcher):
    """Testet den Normalfall: Eine gültige JSON-Datei wird korrekt geladen."""
    # 1. Setup: Gültige JSON im temporären Ordner anlegen
    valid_file = tmp_path / "valid_settings.json"
    valid_file.write_text('{"volume": 80, "language": "de"}', encoding="utf-8")

    # 2. Aktion
    result = _safe_json_load(str(valid_file))

    # 3. Assertions (Prüfungen)
    assert result == {"volume": 80, "language": "de"}
    assert SysEvents.FILE_CORRUPTED not in event_catcher.fired_events


def test_safe_json_load_missing_file(tmp_path, event_catcher):
    """Testet den Fallback: Wenn keine Datei existiert, soll ein leeres Dict zurückkommen."""
    missing_file = tmp_path / "does_not_exist.json"

    result = _safe_json_load(str(missing_file))

    assert result == {}
    assert SysEvents.FILE_CORRUPTED not in event_catcher.fired_events


def test_safe_json_load_corrupted_file(tmp_path, event_catcher):
    """
    Testet den 'Fail Fast' Mechanismus!
    Eine zerstörte Datei muss isoliert und ein Fehler-Event gefeuert werden.
    """
    # 1. Setup: Wir schreiben absichtlich Müll in die Datei (kein valides JSON)
    corrupted_file = tmp_path / "broken_settings.json"
    corrupted_file.write_text('{ das_ist_kein_json: 123, "fehlende_klammer" }', encoding="utf-8")

    # 2. Aktion
    result = _safe_json_load(str(corrupted_file))

    # 3. Assertions (Prüfungen)
    assert result == {}

    backup_file = str(corrupted_file) + ".corrupt.bak"
    assert os.path.exists(backup_file)

    # NEU: Stark typisiertes Event prüfen
    assert SysEvents.FILE_CORRUPTED in event_catcher.fired_events

    assert event_catcher.event_data[SysEvents.FILE_CORRUPTED]["file"] == "broken_settings.json"