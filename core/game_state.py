import json
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

        # NEU: Aufteilung in Basis-Ordner, Match-Ordner und standardisierte ZIP
        self.local_drive_folder = ""
        self.match_folder_name = ""
        self.project_filename = "project.zip"  # Heißt ab jetzt immer so!

        self.times = {}
        self.bonus_texts = {}
        self.active_player = None
        self.ready_players = set()
        self.eliminated_players = set()

    @property
    def local_match_dir(self):
        """Der Pfad zum aktuellen Match-Ordner."""
        if self.match_folder_name:
            return os.path.join(self.local_drive_folder, self.match_folder_name)
        return self.local_drive_folder

    @property
    def local_project_path(self):
        """Der Pfad zur eigentlichen ZIP-Datei im Match-Ordner."""
        return os.path.join(self.local_match_dir, self.project_filename)

    def load_sync_data(self, data):
        self.players = data.get("players", [])
        self.active_players = list(self.players)
        self.start_time_minutes = data.get("start_time_minutes", 15)
        self.penalty_seconds = data.get("penalty_seconds", 0)
        self.distribute_time = data.get("distribute_time", False)

        # NEU: Match-Ordner wird vom Host an die Clients synchronisiert
        self.match_folder_name = data.get("match_folder_name", "")
        self.project_filename = data.get("project_filename", "project.zip")

        for player in self.players:
            if player not in self.times:
                self.times[player] = self.start_time_minutes * 60
                self.bonus_texts[player] = ""

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
        if player_name in self.times:
            self.times[player_name] -= elapsed_seconds

    def eliminate_player(self, player_name):
        if player_name in self.active_players:
            self.active_players.remove(player_name)
        self.eliminated_players.add(player_name)

    def distribute_bonus_time(self, remaining_time):
        if not self.distribute_time or len(self.active_players) == 0:
            return
        bonus = remaining_time / len(self.active_players)
        for p in self.active_players:
            self.times[p] += bonus
            self.bonus_texts[p] = f" (+{int(bonus)}s)"

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