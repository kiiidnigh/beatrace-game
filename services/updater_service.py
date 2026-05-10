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
import customtkinter as ctk

from config.settings import VERSION
from core.i18n import translate as t
from utils.ui_utils import get_centered_geometry
from ui.components.custom_popup import CustomPopup

GITHUB_OWNER = "kiiidnigh"
GITHUB_REPO = "beatrace-game"


class UpdaterService:
    def __init__(self, root_window):
        self.root = root_window
        self.api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
        self.loading_window = None

    def check_for_updates(self):
        logging.info(f"[Updater] Prüfe auf Updates... Aktuelle Version: {VERSION}")
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

            if self._is_newer_version(VERSION, latest_version):
                logging.info(f"[Updater] Neue Version gefunden: {latest_version}")

                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break

                if download_url:
                    self.root.after(0, lambda: self._prompt_update(latest_version, download_url))

        except requests.RequestException as e:
            logging.error(f"[Updater] Fehler bei der Update-Prüfung: {e}")

    def _is_newer_version(self, current_ver, latest_ver):
        """Kugelsichere Versionsprüfung, auch wenn 'v1.4-beta' Strings verwendet werden."""
        try:
            curr = [int(x) for x in re.findall(r'\d+', current_ver)]
            latest = [int(x) for x in re.findall(r'\d+', latest_ver)]

            # Längen angleichen (z.B. "1.4" vs "1.4.0")
            while len(curr) < len(latest): curr.append(0)
            while len(latest) < len(curr): latest.append(0)

            return latest > curr
        except Exception:
            return False

    def _prompt_update(self, latest_version, download_url):
        msg = t("updater.available_msg").replace("{version}", latest_version)

        CustomPopup(
            master=self.root,
            title=t("updater.available_title"),
            message=msg,
            icon="🚀",
            btn_color="#1DB954",
            sound_type="info",
            show_cancel=True,
            confirm_text=t("common.yes"),
            cancel_text=t("common.no"),
            on_confirm_callback=lambda: self._start_update_process(download_url)
        )

    def _start_update_process(self, download_url):
        self._show_loading_ui()
        threading.Thread(target=self._download_and_install, args=(download_url,), daemon=True).start()

    def _show_loading_ui(self):
        self.loading_window = ctk.CTkToplevel(self.root)
        self.loading_window.title(t("updater.loading_title"))
        self.loading_window.attributes('-topmost', True)
        self.loading_window.resizable(False, False)

        self.loading_window.transient(self.root)
        self.loading_window.grab_set()
        self.loading_window.geometry(get_centered_geometry(self.root, width=400, height=220))

        self.lbl_status = ctk.CTkLabel(self.loading_window, text=t("updater.progress_connecting"),
                                       font=("Helvetica", 14, "bold"), text_color="#1DB954")
        self.lbl_status.pack(pady=(30, 15))

        self.progress_bar = ctk.CTkProgressBar(self.loading_window, width=300, height=15, progress_color="#1DB954")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.lbl_percent = ctk.CTkLabel(self.loading_window, text="0%", font=("Helvetica", 14), text_color="gray")
        self.lbl_percent.pack()

        self.root.update()

    def _update_ui(self, progress, status_text=None):
        if self.loading_window and self.loading_window.winfo_exists():
            self.progress_bar.set(progress)
            self.lbl_percent.configure(text=f"{int(progress * 100)}%")
            if status_text:
                self.lbl_status.configure(text=status_text)

    def _download_and_install(self, download_url):
        try:
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "Beatrace_Update_Installer.exe")

            response = requests.get(download_url, stream=True, timeout=15)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            self.root.after(0, lambda: self._update_ui(0.0, t("updater.progress_downloading")))

            with open(installer_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = downloaded / total_size
                            # Aktualisiere das UI nur, wenn es sich lohnt (spart CPU)
                            if int(progress * 100) % 2 == 0:
                                self.root.after(0, lambda p=progress: self._update_ui(p))

            logging.info(f"[Updater] Installer erfolgreich heruntergeladen.")
            self.root.after(0, lambda: self._update_ui(1.0, t("updater.progress_installing")))

            # === DER SILENT-HACK ===
            # Wenn die App als .exe läuft, generieren wir ein Script, das die Installation
            # durchführt, während Beatrace bereits komplett geschlossen ist.
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                bat_path = os.path.join(temp_dir, "beatrace_auto_updater.bat")

                # Das Batch-Skript:
                # 1. Wartet 2 Sekunden, damit sich Beatrace.exe sicher schließen kann.
                # 2. Führt den Installer komplett unsichtbar aus.
                # 3. Startet die aktualisierte Beatrace.exe wieder.
                # 4. Löscht sich selbst.
                bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
"{installer_path}" /VERYSILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS
start "" "{exe_path}"
del "%~f0"
"""
                with open(bat_path, "w", encoding="utf-8") as bat_file:
                    bat_file.write(bat_content)

                # Skript versteckt (ohne Konsolenfenster) starten
                subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # Fallback für Entwicklungsmodus (nur starten, nicht überschreiben)
                subprocess.Popen([installer_path])

            # Suizid der App: Schließt alles sofort, damit InnoSetup die Dateien freigeben kann.
            os._exit(0)

        except Exception as e:
            logging.error(f"[Updater] Fehler beim Update: {e}")
            error_msg = t("updater.error_msg").replace("{error}", str(e))
            self.root.after(0, lambda: self._handle_error(error_msg))

    def _handle_error(self, message):
        if self.loading_window and self.loading_window.winfo_exists():
            self.loading_window.destroy()

        CustomPopup(
            master=self.root,
            title=t("updater.error_title"),
            message=message,
            icon="❌",
            btn_color="#c0392b",
            sound_type="error"
        )