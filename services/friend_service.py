# ================================================
# FILE: services/friend_service.py
# ================================================
import logging
from utils.file_utils import load_social, save_social
from core.event_bus import EventBus
from services.base_service import BaseService

class FriendService(BaseService):
    def __init__(self):
        super().__init__()
        self._social_data = load_social()
        if "friends" not in self._social_data:
            self._social_data["friends"] = {}
        self.register_listeners()

    def _save(self):
        save_social(self._social_data)

    def get_friends(self):
        return self._social_data.get("friends", {})

    def add_friend(self, name, identity_string):
        if "#" not in identity_string:
            return False
        pub_id, token = identity_string.split("#", 1)
        self._social_data["friends"][pub_id] = {"name": name, "token": token}
        self._save()
        logging.info(f"[FriendService] Freund '{name}' ({pub_id}) hinzugefügt/aktualisiert.")
        EventBus.emit("SOCIAL_FRIENDS_UPDATED")
        return True

    def update_friend_name(self, pub_id, new_name):
        friends = self._social_data["friends"]
        if pub_id in friends and friends[pub_id].get("name") != new_name:
            old_name = friends[pub_id].get("name")
            friends[pub_id]["name"] = new_name
            self._save()
            logging.info(f"[FriendService] Freund hat Namen geändert: {old_name} -> {new_name}")
            EventBus.emit("SOCIAL_FRIENDS_UPDATED")

    def remove_friend(self, pub_id):
        if pub_id in self._social_data["friends"]:
            del self._social_data["friends"][pub_id]
            self._save()
            logging.info(f"[FriendService] Freund entfernt: {pub_id}")
            EventBus.emit("SOCIAL_FRIENDS_UPDATED")