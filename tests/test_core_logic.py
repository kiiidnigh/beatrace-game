# ================================================
# FILE: tests/test_core_logic.py
# ================================================
import pytest
from services.match_export_service import MatchExportService


# --- PARAMETRISIERTER TEST (DRY) ---
# Wir schreiben den Test exakt 1x, aber pytest führt ihn 6x mit diesen Werten aus!
@pytest.mark.parametrize("input_seconds, expected_string", [
    (0, "00:00.0"),
    (60, "01:00.0"),
    (65.5, "01:05.5"),
    (600, "10:00.0"),
    (-15, "00:00.0"),  # Edge Case: Negative Zeit (sollte auf 0 gecappt werden)
    (3599.9, "59:59.9")  # Edge Case: Fast eine Stunde
])
def test_time_formatting(input_seconds, expected_string):
    """Prüft, ob der MatchExportService die Zeit immer sauber ins OBS-Format wandelt."""
    result = MatchExportService.format_time(input_seconds)
    assert result == expected_string


@pytest.mark.parametrize("remaining_time, active_player_count, expected_bonus", [
    (600, 3, 200),  # 600s / 3 Spieler = 200s Bonus
    (100, 2, 50),  # 100s / 2 Spieler = 50s Bonus
    (0, 4, 0),  # Keine Restzeit = Kein Bonus
])
def test_time_distribution(empty_game_state, remaining_time, active_player_count, expected_bonus):
    """Prüft, ob die Zeitverteilung (Distribute Time) mathematisch korrekt aufgeteilt wird."""
    state = empty_game_state
    state.distribute_time = True

    # Dummy-Spieler generieren
    state.active_players = [f"Player{i}" for i in range(active_player_count)]
    for p in state.active_players:
        state.set_player_time(p, 100)  # Jeder hat initial 100s

    state.distribute_bonus_time(remaining_time)

    # Jeder aktive Spieler sollte jetzt seine 100s + den erwarteten Bonus haben
    for p in state.active_players:
        assert state.get_player_time(p) == 100 + expected_bonus