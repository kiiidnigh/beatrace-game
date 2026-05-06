import os
import time
import csv
import logging
from core.event_bus import EventBus


class TimelineService:
    def __init__(self, match_dir, is_host):
        self.match_dir = match_dir
        self.is_host = is_host
        self.filepath = os.path.join(self.match_dir, "timeline.csv")

        if self.is_host:
            self._ensure_file_exists()
            logging.info(f"[TimelineService] Gestartet. CSV liegt in: {self.filepath}")

        self._setup_subscriptions()

    def _ensure_file_exists(self):
        try:
            os.makedirs(self.match_dir, exist_ok=True)
            if not os.path.exists(self.filepath):
                with open(self.filepath, "w", newline='', encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Real_Timestamp", "Event_Type", "Player", "Remaining_Time", "Notiz"])
        except Exception as e:
            logging.error(f"[TimelineService] Fehler beim Erstellen der CSV: {e}")

    def _setup_subscriptions(self):
        # Das ist die Magie! Der Service protokolliert vollautomatisch den Status der App.
        EventBus.subscribe("STATE_MATCH_STARTED", lambda d: self.log_event("MATCH_START", note=d.get("note", "")))
        EventBus.subscribe("STATE_TURN_START",
                           lambda d: self.log_event("TURN_START", d.get("player"), d.get("time_left", 0),
                                                    d.get("note", "")))
        EventBus.subscribe("STATE_PAUSED",
                           lambda d: self.log_event("PAUSE", d.get("player"), d.get("time_left", 0), d.get("note", "")))
        EventBus.subscribe("STATE_RESUMED", lambda d: self.log_event("RESUME", d.get("player"), d.get("time_left", 0),
                                                                     d.get("note", "")))
        EventBus.subscribe("STATE_TURN_END",
                           lambda d: self.log_event("TURN_END", d.get("player"), d.get("time_left", 0),
                                                    d.get("note", "")))
        EventBus.subscribe("STATE_ELIMINATED",
                           lambda d: self.log_event("ELIMINATED", d.get("player"), d.get("time_left", 0),
                                                    d.get("note", "")))
        EventBus.subscribe("STATE_FINISHED",
                           lambda d: self.log_event("FINISHED", d.get("player"), d.get("time_left", 0),
                                                    d.get("note", "")))
        EventBus.subscribe("STATE_GAME_OVER", lambda d: self.log_event("GAME_OVER", note=d.get("note", "")))

    def log_event(self, event_type, player="System", remaining_time=0.0, note=""):
        if not self.is_host:
            return

        timestamp = time.time()
        try:
            with open(self.filepath, "a", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([f"{timestamp:.3f}", event_type, player, round(remaining_time, 2), note])
        except Exception as e:
            logging.error(f"[TimelineService] Schreibfehler: {e}")