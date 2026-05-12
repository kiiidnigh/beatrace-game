# ================================================
# FILE: services/identity_service.py
# ================================================
import uuid
import secrets
import logging
from utils.file_utils import load_social, save_social


class IdentityService:
    @staticmethod
    def get_or_create_identity():
        social_data = load_social()

        friend_id = social_data.get("friend_id")
        if friend_id and "#" in friend_id:
            return friend_id

        public_id = str(uuid.uuid4()).split("-")[0].upper()
        private_token = secrets.token_urlsafe(6)

        new_identity = f"{public_id}#{private_token}"

        social_data["friend_id"] = new_identity
        save_social(social_data)

        logging.info(f"[Identity] Neue Identität erstellt: {new_identity}")
        return new_identity

    @staticmethod
    def get_public_id():
        return IdentityService.get_or_create_identity().split("#")[0]

    @staticmethod
    def get_private_token():
        return IdentityService.get_or_create_identity().split("#")[1]