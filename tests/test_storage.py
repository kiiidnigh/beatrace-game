# ================================================
# FILE: tests/test_storage.py
# ================================================
import pytest
import subprocess
from services.storage.rclone_adapter import RcloneCloudAdapter
from services.storage.base_adapter import SyncException


def test_rclone_upload_success(monkeypatch):
    """Prüft ob der Rclone Adapter korrekte Subprocess Aufrufe macht."""
    adapter = RcloneCloudAdapter()

    # Fake Subprocess Call
    executed_command = []

    def fake_run(cmd, **kwargs):
        executed_command.extend(cmd)

        class FakeResult:
            stdout = "success"

        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("os.path.exists", lambda path: True)  # Täuscht vor, dass rclone.exe da ist

    adapter.upload("C:\\local.zip", "Remote_Match/project.zip")

    # Assertions
    assert "copyto" in executed_command
    assert "C:\\local.zip" in executed_command
    assert "beatrace_drive:Remote_Match/project.zip" in executed_command


def test_rclone_fail_fast_on_missing_exe(monkeypatch):
    """Testet das Fail Fast Prinzip: Wenn Rclone fehlt, muss es sofort knallen."""
    adapter = RcloneCloudAdapter()

    # Täuscht vor, dass die Datei NICHT existiert
    monkeypatch.setattr("os.path.exists", lambda path: False)

    with pytest.raises(SyncException) as excinfo:
        adapter.upload("C:\\local.zip", "remote")

    # Prüft nun auf den korrekten deutschen Exception-String der neuen Implementierung
    assert "fehlt" in str(excinfo.value)