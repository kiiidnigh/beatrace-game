# ================================================
# FILE: tests/test_match_logic.py
# ================================================
from core.match_controller import MatchController
from core.events import StateEvents, CmdEvents, UIEvents


def test_turn_end_success(empty_game_state, mock_network, event_catcher):
    """Prüft, ob die Turn-Ende Logik sauber an den nächsten weitergibt."""

    # 1. Setup: 2 Spieler sind im Spiel
    empty_game_state.players = ["P1", "P2"]
    empty_game_state.active_players = ["P1", "P2"]
    empty_game_state.my_name = "P1"
    empty_game_state.active_player = "P1"
    empty_game_state.set_player_time("P1", 600)

    # NEU: Controller wird OHNE den Router initialisiert (Lose Kopplung repariert!)
    controller = MatchController(empty_game_state, mock_network)

    # 2. Aktion: Wir simulieren, dass P1 erfolgreich abspeichert (Die DAW schließt sich)
    controller._handle_turn_end_success({"file_hash": "abc123hash"})

    # 3. Assertions
    # NEU: Verwendung stark typisierter Events
    assert StateEvents.TURN_END in event_catcher.fired_events

    # Das Netzwerk muss den Nachbarn das Ende signalisieren
    assert mock_network.sent_signals[-1]["command"] == "TURN_END"
    assert mock_network.sent_signals[-1]["data"]["file_hash"] == "abc123hash"


def test_game_over_triggers_when_last_player_finishes(empty_game_state, mock_network, event_catcher):
    """Testet das Feuern des Analyse-Events, wenn das Match vorbei ist."""

    # Nur noch P1 ist aktiv (P2 ist schon fertig/ausgeschieden)
    empty_game_state.players = ["P1", "P2"]
    empty_game_state.active_players = ["P1"]
    empty_game_state.my_name = "P1"

    controller = MatchController(empty_game_state, mock_network)

    # P1 gibt als letzter ab
    controller._handle_turn_end_success({"file_hash": "finalhash"})

    # Assertions:
    assert StateEvents.FINISHED in event_catcher.fired_events
    assert StateEvents.GAME_OVER in event_catcher.fired_events

    # NEU: Der Controller darf die UI nicht mehr direkt umschalten!
    # Er muss stattdessen das Analyse-Event feuern, das dann vom Backend bearbeitet wird.
    assert CmdEvents.ANALYZE_MATCH in event_catcher.fired_events