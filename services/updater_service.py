import os
import sys
import tempfile
import threading
import subprocess
import logging
import requests
import customtkinter as ctk
import tkinter.messagebox as messagebox
from config.settings import VERSION

# Deine exakten GitHub-Daten
GITHUB_OWNER = "kiiidnigh"
GITHUB_REPO = "beatrace-game"


class UpdaterService:
    def __init__(self, root_window):
        self.root = root_window
        self.api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

    def check_for_updates(self):
        """Startet die Update-Prüfung in einem Hintergrund-Thread, um die UI nicht einzufrieren."""
        logging.info(f"[Updater] Prüfe auf Updates... Aktuelle Version: {VERSION}")
        threading.Thread(target=self._check_logic, daemon=True).start()

    def _check_logic(self):
        try:
            response = requests.get(self.api_url, timeout=5)
            if response.status_code != 200:
                logging.warning(f"[Updater] Kein Release gefunden oder API Fehler ({response.status_code}).")
                return

            data = response.json()
            latest_version = data.get("tag_name", "").replace("v", "")  # z.B. "1.0.1"

            if not latest_version:
                return

            if self._is_newer_version(VERSION, latest_version):
                logging.info(f"[Updater] Neue Version gefunden: {latest_version}")

                # Suche nach der .exe Datei in den Release-Assets auf GitHub
                assets = data.get("assets", [])
                download_url = None
                for asset in assets:
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break

                if download_url:
                    # Sicher ins Tkinter-UI zurückkehren, um das Pop-up zu zeigen
                    self.root.after(0, lambda: self._prompt_update(latest_version, download_url))

        except requests.RequestException as e:
            logging.error(f"[Updater] Fehler bei der Update-Prüfung: {e}")

    def _is_newer_version(self, current_ver, latest_ver):
        """Vergleicht zwei Version-Strings (z.B. '1.0.0' und '1.0.1')."""
        try:
            current_parts = [int(x) for x in current_ver.split(".")]
            latest_parts = [int(x) for x in latest_ver.split(".")]
            return latest_parts > current_parts
        except Exception:
            return False

    def _prompt_update(self, latest_version, download_url):
        result = messagebox.askyesno(
            "Update verfügbar!",
            f"Eine neue Version von Beatrace ({latest_version}) ist verfügbar.\n\nMöchtest du sie jetzt herunterladen und installieren?"
        )
        if result:
            self._download_and_install(download_url)

    def _download_and_install(self, download_url):
        # Zeige einen Lade-Dialog
        loading_window = ctk.CTkToplevel(self.root)
        loading_window.title("Update")
        loading_window.geometry("300x100")
        loading_window.attributes('-topmost', True)
        ctk.CTkLabel(loading_window, text="Lade Update herunter...\nBitte warten.", font=("Helvetica", 14)).pack(
            expand=True)
        self.root.update()

        try:
            # Lade den Installer in den versteckten Temp-Ordner von Windows
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "Beatrace_Update_Installer.exe")

            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            with open(installer_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logging.info(f"[Updater] Installer erfolgreich nach {installer_path} heruntergeladen.")

            # Starte den neuen Installer und schließe die aktuelle App!
            subprocess.Popen([installer_path])
            sys.exit()

        except Exception as e:
            loading_window.destroy()
            logging.error(f"[Updater] Fehler beim Download des Updates: {e}")
            messagebox.showerror("Update fehlgeschlagen", f"Das Update konnte nicht heruntergeladen werden.\n{e}")