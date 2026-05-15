# ================================================
# FILE: services/daw_service.py
# ================================================
import os
import subprocess
import logging
import zipfile
from monitor.daw_watcher import DAWWatcher
from services.daws import get_current_daw
from core.event_bus import EventBus
from core.events import CmdEvents, SysEvents, UIEvents
from services.base_service import BaseService


class DAWService(BaseService):
    def __init__(self):
        super().__init__()
        self.watcher = DAWWatcher()
        self.daw = get_current_daw()
        logging.info(f"[DAWService] Bereit. Aktuelle DAW: {self.daw.name}")

        # Typisierte Events!
        self._listeners = {
            CmdEvents.LAUNCH_DAW: self._handle_launch,
            CmdEvents.WAIT_DAW_INTERACTION: lambda d: self.watcher.wait_for_interaction(
                callback=lambda: EventBus.emit("DAW_INTERACTION_DETECTED")),
            CmdEvents.WAIT_RESUME_CLICK: lambda d: self.watcher.wait_for_interaction(
                callback=lambda: EventBus.emit("DAW_RESUME_CLICK_DETECTED")),
            CmdEvents.WAIT_DAW_EXIT: lambda d: self.watcher.wait_for_exit(
                callback=lambda: EventBus.emit("DAW_PROCESS_CLOSED")),
            CmdEvents.FORCE_AUTO_SAVE: lambda d: self.watcher.auto_save_and_close(),
            CmdEvents.STOP_DAW_MONITOR: lambda d: self.watcher.stop()
        }
        self.register_listeners()

    def cleanup(self):
        super().cleanup()
        self.watcher.stop()

    def _handle_launch(self, data):
        project_path = data.get("project_path")
        template_path = data.get("template_path")
        executable = self.daw.executable_path

        # Fail Fast: Brich sofort ab, wenn der Pfad fehlt, anstatt später in einen Fehler zu rennen.
        if not executable or not os.path.exists(executable):
            logging.error(f"[DAWService] {self.daw.name} Executable fehlt oder ist ungültig!")
            EventBus.emit(SysEvents.DAW_NOT_FOUND, {"daw_name": self.daw.name})
            # Setze das kleine UI Label zurück
            EventBus.emit(UIEvents.STATUS_UPDATE, {"text": "Warte auf Pfad...", "color": "orange"})
            return

        logging.info(f"[DAWService] Starte {self.daw.name} fuer Projekt: {project_path}")
        try:
            if not os.path.exists(project_path) or os.path.getsize(project_path) == 0:
                if os.path.exists(template_path):
                    with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(template_path, arcname="project.flp")
                else:
                    EventBus.emit("DAW_LAUNCH_ERROR", data={"error": "Template fehlt!"})
                    return

            if os.path.exists(project_path):
                subprocess.Popen([executable, project_path])
            else:
                subprocess.Popen([executable])

            self.watcher.wait_for_start(callback=lambda: EventBus.emit("DAW_LAUNCH_SUCCESS"))
        except Exception as e:
            logging.error(f"[DAWService] Kritischer Fehler beim Launch: {e}", exc_info=True)
            EventBus.emit("DAW_LAUNCH_ERROR", data={"error": str(e)})