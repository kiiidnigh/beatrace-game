# ================================================
# FILE: tests/test_lobby_network.py
# ================================================
from services.lobby_service import LobbyService


def test_host_distributes_state_on_join(empty_game_state, mock_network):
    """
    Testet SoC: Verarbeitet der LobbyService einen Client-Join richtig
    und schickt er den Sync-Status an alle zurück?
    """
    # 1. Setup: Host vorbereiten
    empty_game_state.is_host = True
    empty_game_state.my_name = "HostPlayer"
    empty_game_state.room_code = "ABCDE"

    lobby = LobbyService(empty_game_state, mock_network)

    # 2. Aktion: Wir tun so, als würde ein Client über MQTT joinen
    lobby._on_client_join({"sender": "GastSpieler"})

    # 3. Assertions (Erwartung)
    # Wurde der Spieler registriert?
    assert "GastSpieler" in empty_game_state.players
    assert "GastSpieler" in empty_game_state.active_players

    # Hat der Host sofort eine Antwort (SYNC_STATE) ins Netzwerk geschickt?
    assert len(mock_network.sent_signals) > 0
    assert mock_network.sent_signals[-1]["command"] == "SYNC_STATE"

    # Sind die Daten im Paket korrekt?
    sent_data = mock_network.sent_signals[-1]["data"]
    assert "GastSpieler" in sent_data["players"]


def test_client_receives_sync_data(empty_game_state, mock_network):
    """Prüft, ob ein Client empfangene Daten korrekt in seinen eigenen State lädt."""
    empty_game_state.is_host = False
    empty_game_state.my_name = "GastSpieler"

    lobby = LobbyService(empty_game_state, mock_network)

    # Wir simulieren ein eintreffendes Netzwerkpaket vom Host
    fake_payload = {
        "data": {
            "players": ["HostPlayer", "GastSpieler"],
            "start_time_minutes": 20,
            "verified_players": ["HostPlayer"]
        }
    }

    lobby._on_sync_state(fake_payload)

    # Hat der Client die Zeiten und Spieler übernommen?
    assert len(empty_game_state.players) == 2
    assert empty_game_state.start_time_minutes == 20
    # Die Zeit muss automatisch in Sekunden umgerechnet worden sein
    assert empty_game_state.get_player_time("HostPlayer") == 1200