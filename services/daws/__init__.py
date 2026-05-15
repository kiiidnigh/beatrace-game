# ================================================
# FILE: services/daws/__init__.py
# ================================================
from .fl_studio_adapter import FLStudioAdapter

# Hier registrieren wir in Zukunft Ableton, Logic, etc.
AVAILABLE_DAWS = {
    "FL Studio": FLStudioAdapter()
}

def get_current_daw():
    """
    Gibt den aktuell aktiven DAW-Adapter zurück.
    (Vorerst fest auf FL Studio, später kann das aus den Settings.json kommen)
    """
    return AVAILABLE_DAWS["FL Studio"]