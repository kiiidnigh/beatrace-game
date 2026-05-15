# ================================================
# FILE: config/settings.py
# ================================================
import os
import sys

# --- PFAD-LOGIK FÜR DATA SEPARATION ---
# Dieser Pfad zeigt auf C:\Users\Name\AppData\Roaming\Beatrace
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Beatrace')

# Sicherstellen, dass der Basis-Ordner existiert
os.makedirs(APPDATA_DIR, exist_ok=True)

# --- NETZWERK ---
ROOM_SECRET = "beatrace_prod_PPnYcSInd3pi03o9db16LKaU86ZmlgQx"
BROKER = "broker.hivemq.com"
PORT = 1883

# --- SPIEL-EINSTELLUNGEN ---
START_TIME_SECONDS = 15 * 60  # 15 Minuten

# --- PFADE (PYINSTALLER SAFE) ---
# Wenn als kompilierte .exe ausgeführt, nehmen wir den Ordner der .exe
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
# Im Entwicklungsmodus nehmen wir den Root-Ordner des Projekts
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Für den Test simulieren wir Google Drive mit einer lokalen ZIP-Datei im Projektordner
DRIVE_PROJECT_PATH = os.path.join(BASE_DIR, "test_projekt.zip")

VERSION = "1.5.1"

# --- TELEMETRY ---
DISCORD_APP_ID = "1503158856228802560"
CURRENT_LOG_FILE = ""  # Wird zur Laufzeit von main.py gefüllt
TELEMETRY_URL = "https://discord.com/api/webhooks/1501934166080487597/NLo5R-7pdmL_BXBP3yyu3-XdmJW1JrE9HaZjn0iLmatIz7LIXQjx0ojTDAjaE_hklNt0"