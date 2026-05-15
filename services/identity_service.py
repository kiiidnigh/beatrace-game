# ================================================
# FILE: services/identity_service.py
# ================================================
import uuid
import secrets
import logging
from utils.file_utils import load_profile, save_profile
from services.base_service import BaseService

class IdentityService(BaseService):
    def __init__(self):
        super().__init__()
        self._profile = load_profile()
        self._ensure_id()
        self.register_listeners()

    def _save(self):
        save_profile(self._profile)

    def _ensure_id(self):
        friend_id = self._profile.get("friend_id")
        if not friend_id or "#" not in friend_id:
            public_id = str(uuid.uuid4()).split("-")[0].upper()
            private_token = secrets.token_urlsafe(6)
            self._profile["friend_id"] = f"{public_id}#{private_token}"
            self._save()
            logging.info(f"[Identity] Neue permanente ID generiert: {self._profile['friend_id']}")

    def get_or_create_id(self):
        return self._profile.get("friend_id")

    def get_public_id(self):
        return self.get_or_create_id().split("#")[0]

    def get_private_token(self):
        return self.get_or_create_id().split("#")[1]

    def get_display_name(self):
        return self._profile.get("display_name", "")

    def set_display_name(self, name):
        self._profile["display_name"] = name
        self._save()
        logging.info(f"[Identity] Display Name aktualisiert: {name}")