# ================================================
# FILE: services/match_export_service.py
# ================================================
import os
import logging
from services.base_service import BaseService
from utils.file_utils import get_obs_path


class MatchExportService(BaseService):
    """Lagert das Schreiben ins Dateisystem aus dem MatchController aus (SoC / SRP)."""

    def __init__(self, game_state):
        super().__init__()
        self.state = game_state

        safe_name = self.state.my_name.replace(" ", "_").lower()
        self.obs_file_path = get_obs_path(safe_name)

        self._listeners = {
            "OBS_UPDATE": self._on_obs_update,
            "STATE_GAME_OVER": self._generate_match_files
        }
        self.register_listeners()

    @staticmethod
    def format_time(seconds):
        if seconds < 0: seconds = 0
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 10)
        return f"{mins:02d}:{secs:02d}.{millis}"

    def _on_obs_update(self, data):
        status = data.get("status")
        try:
            with open(self.obs_file_path, "w") as f:
                if status:
                    f.write(status)
                else:
                    all_times = self.state.get_all_times_dict()
                    obs_text = " | ".join([f"{p}: {self.format_time(all_times.get(p, 0))}" for p in self.state.players])
                    active = f"[{self.state.active_player}] " if self.state.active_player else "[PAUSE] "
                    f.write(active + obs_text)
        except Exception:
            pass

    def _generate_match_files(self, data=None):
        if not self.state.is_host:
            return

        match_dir = self.state.local_match_dir
        if not match_dir:
            return

        os.makedirs(match_dir, exist_ok=True)
        try:
            with open(os.path.join(match_dir, "summary.txt"), "w", encoding="utf-8") as f:
                f.write("=== BEATRACE ZUSAMMENFASSUNG ===\n\n")

                f.write("[ SPIELER & ZEITEN ]\n")
                all_times = self.state.get_all_times_dict()
                for p in self.state.players:
                    f.write(f"- {p} (Restzeit: {self.format_time(all_times.get(p, 0))})\n")

                f.write("\n[ MATCH AWARDS ]\n")
                awards = self.state.match_stats.get("awards", {})
                if awards:
                    for title, winner in awards.items():
                        clean_title = title.split(" ", 1)[-1] if " " in title else title
                        f.write(f"- {clean_title}: {winner}\n")
                else:
                    f.write("- Keine Auszeichnungen generiert.\n")

                f.write("\n[ PROJEKT FAKTEN ]\n")
                f.write(f"- Dateigröße: {self.state.match_stats.get('file_size', '0.00 MB')}\n")
                f.write(f"- FL Studio Version: {self.state.match_stats.get('fl_version', 'Unbekannt')}\n")

                project_data = self.state.match_stats.get("project_data", {})
                if project_data:
                    for key, val in project_data.items():
                        clean_key = key.split(" ", 1)[-1] if " " in key else key
                        f.write(f"- {clean_key}: {val}\n")
                else:
                    f.write("- Keine detaillierten Metadaten verfügbar.\n")

        except Exception as e:
            logging.error(f"[MatchExportService] Fehler beim Schreiben der summary.txt: {e}")