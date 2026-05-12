# ================================================
# FILE: services/identity_service.py
# ================================================
import uuid
import secrets
import logging
from utils.file_utils import load_profile, save_profile

class IdentityService:
    @staticmethod
    def get_or_create_id():
        profile = load_profile()
        friend_id = profile.get("friend_id")

        # Nur eine neue ID generieren, wenn wir wirklich noch keine haben
        if not friend_id or "#" not in friend_id:
            public_id = str(uuid.uuid4()).split("-")[0].upper()
            private_token = secrets.token_urlsafe(6)
            friend_id = f"{public_id}#{private_token}"

            profile["friend_id"] = friend_id
            save_profile(profile)
            logging.info(f"[Identity] Neue permanente ID generiert: {friend_id}")

        return friend_id

    @staticmethod
    def get_public_id():
        return IdentityService.get_or_create_id().split("#")[0]

    @staticmethod
    def get_private_token():
        return IdentityService.get_or_create_id().split("#")[1]

    # --- NEU: Display Name Management ---
    @staticmethod
    def get_display_name():
        return load_profile().get("display_name", "")

    @staticmethod
    def set_display_name(name):
        profile = load_profile()
        profile["display_name"] = name
        save_profile(profile)
        logging.info(f"[Identity] Display Name aktualisiert: {name}")