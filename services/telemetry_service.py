# ================================================
# FILE: services/telemetry_service.py
# ================================================
import os
import platform
import logging
import threading
import time
import json
import requests
import psutil
from config import settings
from services.base_service import BaseService

class TelemetryService(BaseService):
    def __init__(self):
        super().__init__()
        self.register_listeners()

    def send_crash_report(self, user_message, callback=None):
        def task():
            try:
                log_data = b"Kein Log gefunden."
                if settings.CURRENT_LOG_FILE and os.path.exists(settings.CURRENT_LOG_FILE):
                    with open(settings.CURRENT_LOG_FILE, "rb") as f:
                        log_data = f.read()
                    if len(log_data) > 4000000:
                        log_data = b"[... Log zu gross. Gekuerzt ...]\n\n" + log_data[-4000000:]

                ram = psutil.virtual_memory()
                ram_total = f"{ram.total / (1024**3):.1f} GB"
                ram_free = f"{ram.available / (1024**3):.1f} GB"

                try:
                    disk = psutil.disk_usage(settings.APPDATA_DIR)
                    disk_free = f"{disk.free / (1024**3):.1f} GB"
                except Exception:
                    disk_free = "Unbekannt"

                embed = {
                    "title": "🚨 Neuer Bug Report",
                    "description": f"**Nutzerbeschreibung:**\n```\n{user_message}\n```",
                    "color": 15158332,
                    "fields": [
                        {"name": "💻 System", "value": f"{platform.system()} {platform.release()}", "inline": True},
                        {"name": "📦 App Version", "value": settings.VERSION, "inline": True},
                        {"name": "🧠 CPU", "value": platform.processor() or "Unbekannt", "inline": False},
                        {"name": "🐏 RAM", "value": f"{ram_total} (Frei: {ram_free})", "inline": True},
                        {"name": "💾 Speicher (AppData)", "value": f"Frei: {disk_free}", "inline": True}
                    ],
                    "footer": {"text": "Beatrace Telemetry System"},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }

                payload = {"embeds": [embed]}
                files = {"file": ("beatrace.log", log_data)}
                data = {"payload_json": json.dumps(payload)}

                if settings.TELEMETRY_URL.startswith("https://discord.com/api/webhooks/"):
                    response = requests.post(settings.TELEMETRY_URL, data=data, files=files, timeout=15)
                    response.raise_for_status()
                else:
                    logging.info("[Telemetry] Dummy-Upload simuliert (keine Webhook-URL in settings.py gesetzt).")
                    time.sleep(1.5)

                logging.info("[Telemetry] Log & Telemetry an Entwickler gesendet.")
                if callback: callback(True)
            except Exception as e:
                logging.error(f"[Telemetry] Fehler beim Senden: {e}")
                if callback: callback(False)

        threading.Thread(target=task, daemon=True).start()