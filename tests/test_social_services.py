# ================================================
# FILE: tests/test_social_services.py
# ================================================
from services.friend_service import FriendService
from core.events import SocialEvents


def test_friend_service_add_and_remove(event_catcher):
    """
    Testet den Stateful-Service.
    Löst er die richtigen Events aus und speichert er im RAM?
    """
    service = FriendService()

    # 1. Freund hinzufügen
    success = service.add_friend("Max", "PUB123#TOKEN456")

    # Assertions (Hinzufügen)
    assert success is True
    assert SocialEvents.FRIENDS_UPDATED in event_catcher.fired_events

    friends = service.get_friends()
    assert "PUB123" in friends
    assert friends["PUB123"]["name"] == "Max"
    assert friends["PUB123"]["token"] == "TOKEN456"

    # Event-Spion zurücksetzen
    event_catcher.fired_events.clear()

    # 2. Freund entfernen
    service.remove_friend("PUB123")

    # Assertions (Entfernen)
    assert "PUB123" not in service.get_friends()
    assert SocialEvents.FRIENDS_UPDATED in event_catcher.fired_events


def test_friend_service_rejects_invalid_id():
    """Fail Fast: Prüft, ob unsinnige IDs sofort abgeblockt werden."""
    service = FriendService()

    success = service.add_friend("Hacker", "INVALID_ID_FORMAT")

    assert success is False
    assert len(service.get_friends()) == 0