import os


class GameState:
    def __init__(self):
        self.players = []
        self.active_players = []
        self.my_name = ""
        self.room_code = ""
        self.is_host = False

        self.start_time_minutes = 15
        self.penalty_seconds = 0
        self.distribute_time = False

        # Aufteilung in Basis-Ordner, Match-Ordner und standardisierte ZIP
        self.local_drive_folder = ""
        self.match_folder_name = ""
        self.project_filename = "project.zip"

        # Diese Variable muss immer existieren, damit der Client nicht abstürzt!
        self.selected_template_path = ""

        # Gekapselte Dictionaries für Zeiten und Texte
        self._times = {}
        self._bonus_texts = {}

        self.active_player = None
        self.ready_players = set()
        self.eliminated_players = set()

        # NEU: Zentraler Cache für die finalen Match Statistiken (DRY Prinzip)
        self.match_stats = {}

    def reset_match_data(self):
        """Setzt alle laufenden Spieldaten sicher zurück (z.B. beim Betreten des Hauptmenüs)."""
        self.players.clear()
        self.active_players.clear()
        self.ready_players.clear()
        self.eliminated_players.clear()
        self._times.clear()
        self._bonus_texts.clear()
        self.match_stats.clear()  # NEU
        self.active_player = None
        self.room_code = ""

    @property
    def local_match_dir(self):
        """Der Pfad zum aktuellen Match-Ordner."""
        if not self.local_drive_folder:
            return ""

        if self.match_folder_name:
            return os.path.join(self.local_drive_folder, self.match_folder_name)

        return self.local_drive_folder

    @property
    def local_project_path(self):
        """Der Pfad zur eigentlichen ZIP-Datei im Match-Ordner."""
        match_dir = self.local_match_dir
        if not match_dir or not self.project_filename:
            return ""

        return os.path.join(match_dir, self.project_filename)

    def get_player_time(self, player_name, default=0):
        """Gibt die Zeit eines Spielers sicher zurück."""
        return self._times.get(player_name, default)

    def set_player_time(self, player_name, time_seconds):
        """Setzt die Zeit eines Spielers sicher."""
        self._times[player_name] = time_seconds

    def get_bonus_text(self, player_name):
        """Gibt den Bonustext eines Spielers sicher zurück."""
        return self._bonus_texts.get(player_name, "")

    def set_bonus_text(self, player_name, text):
        """Setzt den Bonustext eines Spielers sicher."""
        self._bonus_texts[player_name] = text

    def get_all_times_dict(self):
        """Gibt eine Kopie der Zeiten für OBS oder UI zurück."""
        return dict(self._times)

    def load_sync_data(self, data):
        self.players = data.get("players", [])
        self.active_players = list(self.players)
        self.start_time_minutes = data.get("start_time_minutes", 15)
        self.penalty_seconds = data.get("penalty_seconds", 0)
        self.distribute_time = data.get("distribute_time", False)

        self.match_folder_name = data.get("match_folder_name", "")
        self.project_filename = data.get("project_filename", "project.zip")

        for player in self.players:
            if player not in self._times:
                self.set_player_time(player, self.start_time_minutes * 60)
                self.set_bonus_text(player, "")

    def export_sync_data(self):
        return {
            "players": self.players,
            "start_time_minutes": self.start_time_minutes,
            "penalty_seconds": self.penalty_seconds,
            "distribute_time": self.distribute_time,
            "match_folder_name": self.match_folder_name,
            "project_filename": self.project_filename
        }

    def update_time(self, player_name, elapsed_seconds):
        if player_name in self._times:
            self._times[player_name] -= elapsed_seconds

    def eliminate_player(self, player_name):
        if player_name in self.active_players:
            self.active_players.remove(player_name)
        self.eliminated_players.add(player_name)

    def distribute_bonus_time(self, remaining_time):
        if not self.distribute_time or len(self.active_players) == 0:
            return
        bonus = remaining_time / len(self.active_players)
        for p in self.active_players:
            current_time = self.get_player_time(p)
            self.set_player_time(p, current_time + bonus)
            self.set_bonus_text(p, f" (+{int(bonus)}s)")

    def get_next_active_player(self, last_player):
        if not self.active_players:
            return None
        try:
            idx = self.players.index(last_player)
        except ValueError:
            return self.active_players[0]

        for i in range(1, len(self.players) + 1):
            next_idx = (idx + i) % len(self.players)
            next_p = self.players[next_idx]
            if next_p in self.active_players:
                return next_p
        return None