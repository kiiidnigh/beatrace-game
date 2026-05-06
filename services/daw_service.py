import os
import subprocess
import logging
import zipfile
from config import settings
from monitor.fl_watcher import FLWatcher
from core.event_bus import EventBus


class DAWService:
    def __init__(self):
        self.watcher = FLWatcher()
        self.current_daw_path = settings.FL_STUDIO_PATH
        logging.info("[DAWService] Bereit. Wartet auf Befehle.")
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        EventBus.subscribe("CMD_LAUNCH_DAW", self._handle_launch)
        EventBus.subscribe("CMD_WAIT_DAW_INTERACTION", lambda d: self.watcher.wait_for_interaction(
            callback=lambda: EventBus.emit("DAW_INTERACTION_DETECTED")))
        EventBus.subscribe("CMD_WAIT_DAW_EXIT",
                           lambda d: self.watcher.wait_for_exit(callback=lambda: EventBus.emit("DAW_PROCESS_CLOSED")))
        EventBus.subscribe("CMD_FORCE_AUTO_SAVE", lambda d: self.watcher.auto_save_and_close())
        EventBus.subscribe("CMD_STOP_DAW_MONITOR", lambda d: self.watcher.stop())

    def _handle_launch(self, data):
        project_path = data.get("project_path")
        template_path = data.get("template_path")

        logging.info(f"[DAWService] Starte DAW fuer Projekt: {project_path}")
        try:
            if not os.path.exists(project_path) or os.path.getsize(project_path) == 0:
                if os.path.exists(template_path):
                    with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(template_path, arcname="project.flp")
                else:
                    EventBus.emit("DAW_LAUNCH_ERROR", data={"error": "Template fehlt!"})
                    return

            if os.path.exists(project_path):
                subprocess.Popen([self.current_daw_path, project_path])
            else:
                subprocess.Popen([self.current_daw_path])

            self.watcher.wait_for_start(callback=lambda: EventBus.emit("DAW_LAUNCH_SUCCESS"))
        except Exception as e:
            logging.error(f"[DAWService] Kritischer Fehler beim Launch: {e}", exc_info=True)
            EventBus.emit("DAW_LAUNCH_ERROR", data={"error": str(e)})