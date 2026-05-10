# ================================================
# FILE: services/flp_analyzer_service.py
# ================================================
import os
import zipfile
import tempfile
import csv
import logging
import struct
from collections import Counter
from core.i18n import translate

try:
    import pyflp
    HAS_PYFLP = True
except ImportError:
    HAS_PYFLP = False


class FLPAnalyzerService:
    @staticmethod
    def _extract_bpm_raw(flp_path):
        """Kugelsichere Hex-Sniper Methode für die BPM."""
        try:
            with open(flp_path, 'rb') as f:
                data = f.read()

                offset = 0
                while True:
                    offset = data.find(b'\x9C', offset)
                    if offset == -1:
                        break

                    if offset + 5 <= len(data):
                        raw_bpm = data[offset + 1: offset + 5]
                        bpm_int = struct.unpack('<I', raw_bpm)[0]
                        if 10000 <= bpm_int <= 522000:
                            return str(round(bpm_int / 1000, 1))

                    offset += 1
        except Exception as e:
            logging.error(f"[Analyzer] Raw BPM Extract Fehler: {e}")

        return None

    @staticmethod
    def analyze_match(game_state):
        stats = {
            "fl_version": translate("common.unknown"),
            "file_size": "0.00 MB",
            "project_data": {},
            "awards": {}
        }

        match_dir = game_state.local_match_dir
        if not match_dir or not os.path.exists(match_dir):
            match_dir = os.path.join(game_state.local_drive_folder, game_state.match_folder_name)

        zip_path = game_state.local_project_path
        if not zip_path or not os.path.exists(zip_path):
            zip_path = os.path.join(match_dir, game_state.project_filename)

        logging.info(f"[Analyzer] Suche nach Timeline in: {match_dir}")
        logging.info(f"[Analyzer] Suche nach ZIP-Projekt in: {zip_path}")

        # ====================================================
        # 1. TIMELINE ANALYSE (Spielerverhalten & Awards)
        # ====================================================
        turn_count = 0
        timeline_path = os.path.join(match_dir, "timeline.csv")

        if os.path.exists(timeline_path):
            try:
                turn_durations = []
                clutch_counts = {}
                pause_counts = {}
                eliminated_first = None

                last_start_time = 0
                current_player = None

                with open(timeline_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        evt = row.get("Event_Type")
                        player = row.get("Player")

                        try:
                            ts = float(row.get("Real_Timestamp", 0))
                            rem_time = float(row.get("Remaining_Time", 0))
                        except ValueError:
                            continue

                        if evt == "TURN_START":
                            last_start_time = ts
                            current_player = player
                        elif evt == "TURN_END":
                            turn_count += 1
                            if current_player == player and last_start_time > 0:
                                duration = ts - last_start_time
                                turn_durations.append((player, duration))

                                if 0 < rem_time < 15.0:
                                    clutch_counts[player] = clutch_counts.get(player, 0) + 1

                        elif evt == "PAUSE":
                            pause_counts[player] = pause_counts.get(player, 0) + 1

                        elif evt == "ELIMINATED":
                            if not eliminated_first:
                                eliminated_first = player

                stats["project_data"][translate("analyzer.data_passes")] = str(turn_count)

                if turn_durations:
                    valid_turns = [tr for tr in turn_durations if tr[1] > 2.0]
                    if valid_turns:
                        fastest = min(valid_turns, key=lambda x: x[1])
                        desc = translate("analyzer.award_hot_potato_desc").format(player=fastest[0], secs=int(fastest[1]))
                        stats["awards"][translate("analyzer.award_hot_potato_title")] = desc

                    slowest = max(turn_durations, key=lambda x: x[1])
                    desc = translate("analyzer.award_thinker_desc").format(player=slowest[0], secs=int(slowest[1]))
                    stats["awards"][translate("analyzer.award_thinker_title")] = desc

                    player_avg = {}
                    for p in game_state.players:
                        p_turns = [d for pl, d in turn_durations if pl == p]
                        if p_turns:
                            player_avg[p] = sum(p_turns) / len(p_turns)

                    if player_avg:
                        pacer = min(player_avg.items(), key=lambda x: x[1])
                        desc = translate("analyzer.award_pacer_desc").format(player=pacer[0], secs=int(pacer[1]))
                        stats["awards"][translate("analyzer.award_pacer_title")] = desc

                if clutch_counts:
                    clutch_king = max(clutch_counts.items(), key=lambda x: x[1])
                    desc = translate("analyzer.award_clutch_desc").format(player=clutch_king[0], count=clutch_king[1])
                    stats["awards"][translate("analyzer.award_clutch_title")] = desc

                if pause_counts:
                    pause_king = max(pause_counts.items(), key=lambda x: x[1])
                    desc = translate("analyzer.award_tactician_desc").format(player=pause_king[0], count=pause_king[1])
                    stats["awards"][translate("analyzer.award_tactician_title")] = desc

                if eliminated_first:
                    desc = translate("analyzer.award_cheapskate_desc").format(player=eliminated_first)
                    stats["awards"][translate("analyzer.award_cheapskate_title")] = desc

            except Exception as e:
                logging.error(f"[Analyzer] Fehler beim Lesen der Timeline: {e}")
                stats["project_data"][translate("analyzer.data_passes")] = translate("common.error")
        else:
            logging.warning("[Analyzer] Timeline CSV nicht gefunden.")
            stats["project_data"][translate("analyzer.data_passes")] = translate("common.unknown")

        # ====================================================
        # 2. FLP ANALYSE (Musikalische DNA)
        # ====================================================
        if os.path.exists(zip_path):
            size_bytes = os.path.getsize(zip_path)
            stats["file_size"] = f"{size_bytes / (1024 * 1024):.2f} MB"

            if HAS_PYFLP and size_bytes > 0:
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)

                        flp_files = [f for f in os.listdir(temp_dir) if f.endswith(".flp")]
                        if flp_files:
                            flp_path = os.path.join(temp_dir, flp_files[0])

                            raw_bpm = FLPAnalyzerService._extract_bpm_raw(flp_path)
                            stats["project_data"][translate("analyzer.data_bpm")] = raw_bpm if raw_bpm else "140.0"

                            project = pyflp.parse(flp_path)

                            if project.version is not None:
                                stats["fl_version"] = str(project.version)

                            if hasattr(project, 'time_spent') and project.time_spent:
                                days, seconds = project.time_spent.days, project.time_spent.seconds
                                hours = days * 24 + seconds // 3600
                                minutes = (seconds % 3600) // 60
                                stats["project_data"][translate("analyzer.data_time_spent")] = translate(
                                    "analyzer.data_time_spent_val").format(hours=hours, minutes=minutes)

                            if project.channels is not None:
                                samplers = len(list(project.channels.samplers))
                                synths = len(list(project.channels.instruments))
                                stats["project_data"][translate("analyzer.data_audio_midi")] = translate(
                                    "analyzer.data_audio_midi_val").format(samples=samplers, synths=synths)

                                automations = len(list(project.channels.automations))
                                stats["project_data"][translate("analyzer.data_automations")] = str(automations)

                            if hasattr(project, 'patterns'):
                                total_notes = 0
                                for p in project.patterns:
                                    try:
                                        total_notes += len(list(p.notes))
                                    except:
                                        pass
                                stats["project_data"][translate("analyzer.data_midi_notes")] = str(total_notes)

                            plugins = []
                            if project.channels is not None:
                                for inst in project.channels.instruments:
                                    if inst.plugin and inst.plugin.name:
                                        plugins.append(inst.plugin.name)
                            if hasattr(project, 'mixer'):
                                for insert in project.mixer:
                                    for slot in insert:
                                        if slot.plugin and slot.plugin.name:
                                            plugins.append(slot.plugin.name)

                            if plugins:
                                most_common = Counter(plugins).most_common(1)[0]
                                stats["project_data"][translate("analyzer.data_plugin")] = translate(
                                    "analyzer.data_plugin_val").format(plugin=most_common[0], count=most_common[1])

                except Exception as e:
                    error_msg = str(e)
                    if "EventEnum" in error_msg or "enum" in error_msg.lower():
                        logging.warning("[Analyzer] FL Studio Projekt ist zu neu für tiefgehende pyflp Analyse.")
                    else:
                        logging.error(f"[Analyzer] Unerwarteter Fehler bei FLP Analyse: {e}")

        return stats