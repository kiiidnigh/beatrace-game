import os
import customtkinter as ctk

def find_fl_studio_path():
    """Sucht nach FL Studio oder öffnet einen Dialog, falls es nicht gefunden wird."""
    base_path = r"C:\Program Files\Image-Line"

    if os.path.exists(base_path):
        folders = [f for f in os.listdir(base_path) if "FL Studio" in f]
        if folders:
            folders.sort(reverse=True)  # Höchste Version zuerst
            for folder in folders:
                exe_path = os.path.join(base_path, folder, "FL64.exe")
                if os.path.exists(exe_path):
                    return exe_path

    # Wenn nicht gefunden: Nutzer fragen
    print("FL Studio im Standard-Pfad nicht gefunden. Bitte manuell auswählen...")
    root = ctk.CTk()
    root.withdraw()  # Versteckt das leere Hauptfenster

    file_path = ctk.filedialog.askopenfilename(
        title="Bitte wähle deine FL64.exe aus",
        filetypes=[("FL Studio Executable", "FL64.exe")]
    )
    root.destroy()
    return file_path

# --- PFAD-LOGIK FÜR DATA SEPARATION ---
# Dieser Pfad zeigt auf C:\Users\Name\AppData\Roaming\Beatrace
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Beatrace')

# Sicherstellen, dass der Basis-Ordner existiert
os.makedirs(APPDATA_DIR, exist_ok=True)

# --- NETZWERK ---
ROOM_SECRET = "beatrace_super_geheim_445566"  # Später für euch ändern!
BROKER = "broker.hivemq.com"
PORT = 1883

# --- SPIEL-EINSTELLUNGEN ---
START_TIME_SECONDS = 15 * 60  # 15 Minuten

# --- PFADE ---
# Geht vom config-Ordner einen Ordner nach oben zum Hauptverzeichnis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Für den Test simulieren wir Google Drive mit einer lokalen ZIP-Datei im Projektordner
DRIVE_PROJECT_PATH = os.path.join(BASE_DIR, "test_projekt.zip")

FL_STUDIO_PATH = find_fl_studio_path()

VERSION = "1.0.0"


