# ================================================
# FILE: scripts/test_updater.py
# ================================================
import os
import shutil
import json
import glob
import http.server
import socketserver
import threading
import subprocess
import time
import re


def start_server_in_background(server_dir, port):
    os.chdir(server_dir)
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd


def get_version_from_name(filename):
    """Extrahiert die Version aus dem Dateinamen für eine narrensichere Sortierung."""
    match = re.search(r'v(\d+\.\d+\.\d+)', filename)
    return [int(x) for x in match.group(1).split('.')] if match else [0, 0, 0]


def run_auto_test():
    print("\n🚀 BEATRACE FAKE GITHUB SERVER 🚀")
    print("====================================")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    installer_dir = os.path.join(base_dir, "installer")
    server_dir = os.path.join(base_dir, ".update_server")
    dist_dir = os.path.join(base_dir, "dist", "Beatrace")
    exe_path = os.path.join(dist_dir, "Beatrace.exe")
    flag_path = os.path.join(dist_dir, "DEV_UPDATE.flag")

    # 1. Validierungen
    installers = glob.glob(os.path.join(installer_dir, "*.exe"))
    if not os.path.exists(installer_dir) or not installers:
        print("❌ Fehler: Kein fertiger Installer gefunden. Bitte kompiliere zuerst mit Inno Setup!")
        return

    if not os.path.exists(exe_path):
        print("❌ Fehler: Kompilierte Beatrace.exe nicht gefunden. Bitte führe 'pyinstaller Beatrace.spec' aus!")
        return

    # 2. Server Umgebung aufbauen
    if os.path.exists(server_dir):
        shutil.rmtree(server_dir)
    os.makedirs(server_dir)

    # Nimmt immer den Installer mit der höchsten Versionsnummer im Dateinamen
    latest_installer = max(installers, key=get_version_from_name)
    print(f"📦 Verwende Installer: {os.path.basename(latest_installer)}")
    shutil.copy2(latest_installer, os.path.join(server_dir, "Test_Installer.exe"))

    json_data = {
        "tag_name": "v9.9.9",
        "assets": [{"name": "Dummy.exe", "browser_download_url": "http://127.0.0.1:8000/Test_Installer.exe"}]
    }
    with open(os.path.join(server_dir, "latest.json"), "w") as f:
        json.dump(json_data, f, indent=4)

    # 3. Das DEV_UPDATE Flag für die App setzen
    with open(flag_path, "w") as f:
        f.write("test_active")
    print("🚩 Flag 'DEV_UPDATE.flag' erfolgreich gesetzt.")

    # 4. Server starten
    httpd = start_server_in_background(server_dir, 8000)
    print("🌐 Lokaler Fake-GitHub Server läuft auf Port 8000.")

    src_assets = os.path.join(base_dir, "assets")
    dist_assets = os.path.join(dist_dir, "assets")

    if os.path.exists(src_assets):
        print("📁 Kopiere Assets (Sprachen & Sounds) in den Test-Ordner...")
        if os.path.exists(dist_assets):
            shutil.rmtree(dist_assets)  # Falls alt, erst löschen
        shutil.copytree(src_assets, dist_assets)

    # 5. Beatrace starten
    print("🎮 Starte Beatrace automatisch...")
    time.sleep(1)

    try:
        # Popen startet die App, blockiert aber das Terminal nicht
        subprocess.Popen([exe_path])
        print("\n" + "=" * 40)
        print("✅ ALLES BEREIT!")
        print("Die App sollte sich jetzt geöffnet haben und das Update finden.")
        print("Warte den Test ab. Danach kannst du dieses Skript beenden.")
        print("=" * 40)

        # Skript am Leben erhalten, bis User STRG+C drückt
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Test beendet. Räume auf...")

    finally:
        # 6. Aufräumen (Robust gegen Windows Dateisperren)
        print("\n⏳ Fahre Server herunter...")
        httpd.shutdown()
        httpd.server_close()  # Zwingt den Server, alle Dateien loszulassen

        # Wichtig: Wir müssen das Arbeitsverzeichnis verlassen, sonst sperrt Python selbst den Ordner!
        os.chdir(base_dir)

        if os.path.exists(flag_path):
            os.remove(flag_path)

        # Retry-Loop für das Löschen des Ordners (Windows braucht oft 1-2 Sekunden)
        max_retries = 5
        for i in range(max_retries):
            try:
                if os.path.exists(server_dir):
                    shutil.rmtree(server_dir)
                print("🧹 Aufräumen abgeschlossen! Flag entfernt, Server gelöscht.")
                break
            except Exception as e:
                if i < max_retries - 1:
                    time.sleep(1)  # 1 Sekunde warten und nochmal probieren
                else:
                    print(
                        f"⚠️ Hinweis: Der Ordner '.update_server' konnte nicht gelöscht werden, da er noch verwendet wird.")


if __name__ == "__main__":
    run_auto_test()