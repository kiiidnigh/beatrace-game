# ================================================
# FILE: tests/test_game_state.py
# ================================================

def test_get_next_active_player_round_robin(empty_game_state):
    """Testet, ob die Spieler-Reihenfolge korrekt umläuft und Ausgeschiedene überspringt."""
    state = empty_game_state
    state.players = ["Host", "Player2", "Player3"]
    state.active_players = ["Host", "Player2", "Player3"]

    # Normaler Durchlauf
    assert state.get_next_active_player("Host") == "Player2"
    assert state.get_next_active_player("Player2") == "Player3"

    # Wrap-Around (Von P3 zurück zum Host)
    assert state.get_next_active_player("Player3") == "Host"


def test_get_next_active_player_skips_eliminated(empty_game_state):
    """Prüft, ob ausgeschiedene Spieler sauber übersprungen werden."""
    state = empty_game_state
    state.players = ["Host", "Player2", "Player3"]

    # P2 ist rausgeflogen!
    state.active_players = ["Host", "Player3"]

    # Nach dem Host MUSS jetzt Player3 drankommen, nicht P2!
    assert state.get_next_active_player("Host") == "Player3"


def test_prepare_next_match_resets_correctly(empty_game_state):
    """Prüft, ob nach einer Runde der Status sauber für ein Rematch geleert wird."""
    state = empty_game_state
    state.is_host = False
    state.players = ["Host", "Ich"]

    # Wir tun so, als hätte 'Ich' gerade verloren
    state.eliminate_player("Ich")
    assert "Ich" in state.eliminated_players

    # Aktion: Rematch wird vorbereitet
    state.prepare_next_match()

    # Assertions
    assert "Ich" not in state.eliminated_players  # Strafe aufgehoben!
    # Hinweis: Die alte workspace_id Assertion wurde entfernt, da die Rclone-Umstrukturierung
    # nun den cloud_remote_path verwendet und dieser im Rematch bestehen bleibt.
    assert len(state.ready_players) == 2  # Alle sofort wieder ready im Lobby-Raum