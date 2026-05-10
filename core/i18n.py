# ================================================
# FILE: core/i18n.py
# ================================================
import os
import json
import logging
from config import settings
from utils.file_utils import load_prefs


class Translator:
    _instance = None
    _translations = {}
    _current_lang = "en"

    @classmethod
    def initialize(cls):
        """Lädt die Sprachdatei basierend auf den User-Settings."""
        prefs = load_prefs()
        cls._current_lang = prefs.get("language", "en")

        locale_path = os.path.join(settings.BASE_DIR, "assets", "locales", f"{cls._current_lang}.json")

        if not os.path.exists(locale_path):
            logging.warning(f"[i18n] Sprachdatei {cls._current_lang}.json nicht gefunden. Fallback auf 'en'.")
            locale_path = os.path.join(settings.BASE_DIR, "assets", "locales", "en.json")

        try:
            with open(locale_path, "r", encoding="utf-8") as f:
                cls._translations = json.load(f)
            logging.info(f"[i18n] Sprache '{cls._current_lang}' erfolgreich geladen.")
        except Exception as e:
            logging.error(f"[i18n] Fehler beim Laden der Sprachdatei: {e}")
            cls._translations = {}

    @classmethod
    def get(cls, key_path, default=""):
        """
        Holt einen Text anhand eines Pfades (z.B. 'home.btn_host').
        Wenn der Text nicht existiert, wird der Key oder ein Default zurückgegeben.
        """
        if not cls._translations:
            cls.initialize()

        keys = key_path.split('.')
        val = cls._translations
        try:
            for key in keys:
                val = val[key]
            return val
        except (KeyError, TypeError):
            logging.debug(f"[i18n] Fehlender Übersetzungs-Key: {key_path}")
            return default if default else f"[{key_path}]"


def translate(key_path, default=""):
    """Globale Hilfsfunktion für kürzere Aufrufe."""
    return Translator.get(key_path, default)