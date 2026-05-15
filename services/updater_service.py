# ================================================
# FILE: services/updater_service.py
# ================================================
import os
import sys
import tempfile
import threading
import subprocess
import logging
import re
import requests
from config import settings
from services.base_service import BaseService
from core.event_bus import EventBus

GITHUB_OWNER = "kiiidnigh"
GITHUB_REPO = "beatrace-game"


class UpdaterService(BaseService):
    def __init__(self):
        super().__init__()

        flag_path = os.path.join(settings.BASE_DIR, "DEV_UPDATE.flag")
        if os.path.exists(flag_path):
            self.api_url = "http://127.0.0.1:8000/latest.json"
            logging.info("[Updater] ⚠️ DEV_UPDATE.flag gefunden! Nutze lokalen Test-Server.")
        else:
            self.api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

        self._listeners = {
            "CMD_CHECK_FOR_UPDATES": lambda d: self.check_for_updates(),
            "CMD_START_UPDATE": self._start_update_process
        }
        self.register_listeners()

    def check_for_updates(self):
        logging.info(f"[Updater] Prüfe auf Updates... Aktuelle Version: {settings.VERSION}")
        threading.Thread(target=self._check_logic, daemon=True).start()

    def _check_logic(self):
        try:
            response = requests.get(self.api_url, timeout=5)
            if response.status_code != 200:
                logging.warning(f"[Updater] Kein Release gefunden oder API Fehler ({response.status_code}).")
                return

            data = response.json()
            latest_version = data.get("tag_name", "").replace("v", "")

            if not latest_version:
                return

            if self._is_newer_version(settings.VERSION, latest_version):
                logging.info(f"[Updater] Neue Version gefunden: {latest_version}")

                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break

                if download_url:
                    # Entkopplung: UI wird per EventBus benachrichtigt
                    EventBus.emit("UPDATER_AVAILABLE", {"version": latest_version, "url": download_url})

        except requests.RequestException as e:
            logging.error(f"[Updater] Fehler bei der Update-Prüfung: {e}")

    def _is_newer_version(self, current_ver, latest_ver):
        try:
            curr = [int(x) for x in re.findall(r'\d+', current_ver)]
            latest = [int(x) for x in re.findall(r'\d+', latest_ver)]

            while len(curr) < len(latest): curr.append(0)
            while len(latest) < len(curr): latest.append(0)

            return latest > curr
        except Exception:
            return False

    def _start_update_process(self, data):
        download_url = data.get("url")
        if download_url:
            threading.Thread(target=self._download_and_install, args=(download_url,), daemon=True).start()

    def _download_and_install(self, download_url):
        try:
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "Beatrace_Update_Installer.exe")

            response = requests.get(download_url, stream=True, timeout=15)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            EventBus.emit("UPDATER_PROGRESS", {"progress": 0.0, "status": "downloading"})

            with open(installer_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = downloaded / total_size
                            if int(progress * 100) % 2 == 0:
                                EventBus.emit("UPDATER_PROGRESS", {"progress": progress, "status": "downloading"})

            logging.info(f"[Updater] Installer erfolgreich heruntergeladen.")
            EventBus.emit("UPDATER_PROGRESS", {"progress": 1.0, "status": "installing"})

            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                bat_path = os.path.join(temp_dir, "beatrace_auto_updater.bat")

                bat_content = f"""@echo off\ntimeout /t 2 /nobreak > NUL\n"{installer_path}" /VERYSILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS\nstart "" "{exe_path}"\ndel "%~f0"\n"""
                with open(bat_path, "w", encoding="utf-8") as bat_file:
                    bat_file.write(bat_content)

                subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([installer_path])

            os._exit(0)

        except Exception as e:
            logging.error(f"[Updater] Fehler beim Update: {e}")
            EventBus.emit("UPDATER_ERROR", {"error": str(e)})