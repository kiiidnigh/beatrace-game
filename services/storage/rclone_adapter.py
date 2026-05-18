# ================================================
# FILE: services/storage/rclone_adapter.py
# ================================================
import os
import subprocess
import logging
from config import settings
from .base_adapter import BaseStorageAdapter, SyncException


class RcloneCloudAdapter(BaseStorageAdapter):
    """
    Kapselt rclone.exe.
    KISS: Nutzt subprocess für reine Dateitransfers ohne aufwändige OAuth-Server in Python.
    SRP: Diese Klasse kümmert sich NUR um Befehle, nicht um Spiel-Status oder Ordner-Logik.
    """

    def __init__(self):
        # YAGNI: Aktuell nur Windows. Liegt direkt im assets-Ordner.
        self.rclone_exe = os.path.join(settings.BASE_DIR, "assets", "rclone.exe")

        # SRP: Rclone-Konfiguration wird strikt isoliert im AppData-Verzeichnis gespeichert.
        # So pfuscht Rclone nicht in den globalen Windows-Einstellungen des Nutzers herum.
        self.config_path = os.path.join(settings.APPDATA_DIR, "rclone.conf")

        # Der Bezeichner für das Remote-Laufwerk innerhalb der rclone.conf
        self.remote_name = "beatrace_drive"

    def _run_command(self, args: list, timeout: int = None) -> str:
        """
        DRY & Fail Fast: Führt Rclone aus und bricht bei Fehlern sofort ab.
        """
        if not os.path.exists(self.rclone_exe):
            raise SyncException("Rclone.exe fehlt im assets-Ordner! Bitte überprüfe die Installation.")

        # Standard-Konfiguration anhängen
        cmd = [self.rclone_exe] + args + ["--config", self.config_path]

        try:
            # Maskiere Tokens oder Pfade in den Logs, falls nötig. Fürs Erste loggen wir den puren Command (KISS).
            logging.debug(f"[Rclone] Executing: {' '.join(cmd)}")

            # check=True erzwingt Fail Fast: Es wirft CalledProcessError, wenn Rclone einen Exit-Code > 0 liefert
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
            return result.stdout

        except subprocess.CalledProcessError as e:
            # Rclone schreibt Fehler meist in stderr
            error_msg = e.stderr.strip() if e.stderr else e.stdout.strip()
            logging.error(f"[Rclone] Command failed: {error_msg}")
            raise SyncException(f"Cloud-Fehler: {error_msg}")

        except subprocess.TimeoutExpired:
            logging.error("[Rclone] Timeout expired.")
            raise SyncException("Zeitüberschreitung bei der Cloud-Verbindung.")

        except Exception as e:
            logging.error(f"[Rclone] Unerwarteter Systemfehler: {e}")
            raise SyncException(f"Systemfehler beim Ausführen von Rclone: {e}")

    def is_authenticated(self) -> bool:
        """Prüft, ob ein gültiges Token in der Config existiert und Google Drive antwortet."""
        if not os.path.exists(self.config_path):
            return False

        try:
            # Schneller Check (KISS): Kann Rclone den Root-Ordner im konfigurierten Drive lesen?
            # Wenn das fehlschlägt, ist das Token abgelaufen oder nicht vorhanden.
            self._run_command(["lsd", f"{self.remote_name}:"], timeout=10)
            return True
        except SyncException:
            return False

    def authenticate(self):
        """
        Triggert den Google Drive OAuth-Flow.
        Scope 'drive.file' (KISS & Security): Erlaubt Rclone NUR den Zugriff auf Dateien,
        die von Rclone selbst (also Beatrace) erstellt wurden. Der Rest vom Google Drive des Users bleibt tabu!
        """
        logging.info("[Rclone] Starte Google Drive Authentifizierung...")

        # 'config create <name> <type> scope <scope>' ist der Headless-Befehl für den Browser-Flow
        args = ["config", "create", self.remote_name, "drive", "scope", "drive.file"]

        # 5 Min Timeout für den User, um sich im Browser einzuloggen und zu bestätigen
        self._run_command(args, timeout=300)

        logging.info("[Rclone] Authentifizierung erfolgreich abgeschlossen!")

    def upload(self, local_path: str, remote_path: str):
        """
        Lädt eine lokale Datei hoch.
        remote_path sollte das Format "Hauptordner/Matchordner/project.zip" haben.
        """
        remote_full = f"{self.remote_name}:{remote_path}"
        logging.info(f"[Rclone] Uploading {local_path} -> {remote_full}")

        # 'copyto' kopiert eine explizite Datei zu einem expliziten Ziel (SRP)
        self._run_command(["copyto", local_path, remote_full])

    def download(self, remote_path: str, local_path: str):
        """
        Lädt eine Datei herunter.
        remote_path sollte das Format "Hauptordner/Matchordner/project.zip" haben.
        """
        remote_full = f"{self.remote_name}:{remote_path}"
        logging.info(f"[Rclone] Downloading {remote_full} -> {local_path}")

        # 'copyto' von Remote zu Local
        self._run_command(["copyto", remote_full, local_path])