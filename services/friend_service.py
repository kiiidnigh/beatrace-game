# ================================================
# FILE: services/friend_service.py
# ================================================
import logging
from utils.file_utils import load_social, save_social
from core.event_bus import EventBus


class FriendService:
    @staticmethod
    def get_friends():
        return load_social().get("friends", {})

    @staticmethod
    def add_friend(name, identity_string):
        """Wird aufgerufen, wenn eine Freundschaftsanfrage AKZEPTIERT wurde."""
        if "#" not in identity_string:
            return False

        pub_id, token = identity_string.split("#", 1)
        social_data = load_social()

        if "friends" not in social_data:
            social_data["friends"] = {}

        social_data["friends"][pub_id] = {"name": name, "token": token}
        save_social(social_data)

        logging.info(f"[FriendService] Freund '{name}' ({pub_id}) hinzugefügt/aktualisiert.")
        EventBus.emit("SOCIAL_FRIENDS_UPDATED")
        return True

    @staticmethod
    def update_friend_name(pub_id, new_name):
        """Wird aufgerufen, wenn über MQTT ein neuer Name empfangen wird."""
        social_data = load_social()
        friends = social_data.get("friends", {})

        if pub_id in friends and friends[pub_id].get("name") != new_name:
            old_name = friends[pub_id].get("name")
            friends[pub_id]["name"] = new_name
            save_social(social_data)
            logging.info(f"[FriendService] Freund hat Namen geändert: {old_name} -> {new_name}")
            EventBus.emit("SOCIAL_FRIENDS_UPDATED")

    @staticmethod
    def remove_friend(pub_id):
        social_data = load_social()
        if "friends" in social_data and pub_id in social_data["friends"]:
            del social_data["friends"][pub_id]
            save_social(social_data)
            logging.info(f"[FriendService] Freund entfernt: {pub_id}")
            EventBus.emit("SOCIAL_FRIENDS_UPDATED")