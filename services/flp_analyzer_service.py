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
        # Basis-Struktur der Metadaten
        stats = {
            "fl_version": "Unbekannt",
            "file_size": "0.00 MB",
            "project_data": {},  # Hier landen die Fakten
            "awards": {}  # Hier landen die Spieler-Auszeichnungen
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

                                # Clutch (Unter 15 Sek. abgegeben)
                                if 0 < rem_time < 15.0:
                                    clutch_counts[player] = clutch_counts.get(player, 0) + 1

                        elif evt == "PAUSE":
                            pause_counts[player] = pause_counts.get(player, 0) + 1

                        elif evt == "ELIMINATED":
                            if not eliminated_first:
                                eliminated_first = player

                stats["project_data"]["🔄 Weitergaben"] = str(turn_count)

                # Awards berechnen
                if turn_durations:
                    # Heiße Kartoffel (Kürzester, echter Zug > 2 Sekunden)
                    valid_turns = [t for t in turn_durations if t[1] > 2.0]
                    if valid_turns:
                        fastest = min(valid_turns, key=lambda x: x[1])
                        stats["awards"]["🥔 Heiße Kartoffel"] = f"{fastest[0]} (Nur {int(fastest[1])}s behalten)"

                    # Grübler (Längster Zug)
                    slowest = max(turn_durations, key=lambda x: x[1])
                    stats["awards"]["🧠 Der Grübler"] = f"{slowest[0]} ({int(slowest[1])}s am Stück)"

                    # Der Pacer (Durchschnittliche Zugdauer berechnen)
                    player_avg = {}
                    for p in game_state.players:
                        p_turns = [d for pl, d in turn_durations if pl == p]
                        if p_turns:
                            player_avg[p] = sum(p_turns) / len(p_turns)

                    if player_avg:
                        pacer = min(player_avg.items(), key=lambda x: x[1])
                        stats["awards"]["⏱️ Der Pacer"] = f"{pacer[0]} (Ø {int(pacer[1])}s pro Zug)"

                if clutch_counts:
                    clutch_king = max(clutch_counts.items(), key=lambda x: x[1])
                    stats["awards"]["🔥 Clutch King"] = f"{clutch_king[0]} ({clutch_king[1]}x in letzter Sekunde)"

                if pause_counts:
                    pause_king = max(pause_counts.items(), key=lambda x: x[1])
                    stats["awards"]["⏸️ Taktiker"] = f"{pause_king[0]} ({pause_king[1]}x pausiert)"

                if eliminated_first:
                    stats["awards"]["💀 Der Geizhals"] = f"{eliminated_first} (Als erster ausgeschieden)"

            except Exception as e:
                logging.error(f"[Analyzer] Fehler beim Lesen der Timeline: {e}")
                stats["project_data"]["🔄 Weitergaben"] = "Fehler"
        else:
            logging.warning("[Analyzer] Timeline CSV nicht gefunden.")
            stats["project_data"]["🔄 Weitergaben"] = "Unbekannt"

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

                            # BPM Extract (Hex)
                            raw_bpm = FLPAnalyzerService._extract_bpm_raw(flp_path)
                            stats["project_data"]["🥁 Projekt BPM"] = raw_bpm if raw_bpm else "140.0"

                            # FLP Parsen (Ab hier fehleranfällig bei neuen Versionen)
                            project = pyflp.parse(flp_path)

                            if project.version is not None:
                                stats["fl_version"] = str(project.version)

                            # Netto-Arbeitszeit
                            if hasattr(project, 'time_spent') and project.time_spent:
                                days, seconds = project.time_spent.days, project.time_spent.seconds
                                hours = days * 24 + seconds // 3600
                                minutes = (seconds % 3600) // 60
                                stats["project_data"]["⌛ Netto Arbeitszeit"] = f"{hours}h {minutes}m"

                            if project.channels is not None:
                                # Samples vs Synths
                                samplers = len(list(project.channels.samplers))
                                synths = len(list(project.channels.instruments))
                                stats["project_data"]["🎧 Audio vs MIDI"] = f"{samplers} Samples / {synths} Synths"

                                # Automations
                                automations = len(list(project.channels.automations))
                                stats["project_data"]["📉 Automationen"] = str(automations)

                            # Der Mozart Award (Total MIDI Notes)
                            if hasattr(project, 'patterns'):
                                total_notes = 0
                                for p in project.patterns:
                                    try:
                                        total_notes += len(list(p.notes))
                                    except:
                                        pass
                                stats["project_data"]["🎼 MIDI Noten"] = str(total_notes)

                            # Most Used Plugin
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
                                stats["project_data"][
                                    "⭐ Meistgenutztes Plugin"] = f"{most_common[0]} ({most_common[1]}x)"

                except Exception as e:
                    error_msg = str(e)
                    if "EventEnum" in error_msg or "enum" in error_msg.lower():
                        logging.warning("[Analyzer] FL Studio Projekt ist zu neu für tiefgehende pyflp Analyse.")
                    else:
                        logging.error(f"[Analyzer] Unerwarteter Fehler bei FLP Analyse: {e}")

        return stats