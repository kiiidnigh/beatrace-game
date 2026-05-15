# ================================================
# FILE: scripts/run_simulation.py
# ================================================
import subprocess
import argparse
import sys
import os
import time


def start_clients(num_players):
    processes = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_script = os.path.join(base_dir, "main.py")

    print("=============================================")
    print(f"🚀 STARTE BEATRACE MULTIPLAYER SIMULATION ({num_players} Spieler)")
    print("=============================================\n")

    # Wir stellen sicher, dass alle Instanzen den Projekt-Root kennen
    env = os.environ.copy()
    env["PYTHONPATH"] = base_dir

    for i in range(1, num_players + 1):
        # Das '--profile' Flag trennt die AppData-Ordner pro Instanz!
        profile_name = f"SimPlayer_{i}"
        role = "(HOST)" if i == 1 else "(CLIENT)"

        print(f"Starte Instanz {i}: {profile_name} {role}...")

        # Startet den Prozess im Hintergrund
        p = subprocess.Popen(
            [sys.executable, main_script, "--profile", profile_name],
            env=env
        )
        processes.append(p)

        # Kleine Verzögerung, damit die Instanzen sich nicht beim Dateien anlegen stören
        time.sleep(1.5)

    print("\n✅ Alle Instanzen erfolgreich hochgefahren!")
    print("TIPP: Du kannst die Fenster nebeneinander legen und den Netzwerk-Sync testen.")
    print("Drücke STRG+C in dieser Konsole, um alle Instanzen gleichzeitig zu killen.\n")

    try:
        # Hält das Skript am Leben
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n🛑 STRG+C gedrückt. Beende alle Beatrace-Instanzen...")
        for p in processes:
            p.terminate()

        # Hard-Kill falls sie hängen
        time.sleep(1)
        for p in processes:
            if p.poll() is None:
                p.kill()
        print("Sauber beendet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lokale Beatrace Netzwerk-Simulation")
    parser.add_argument(
        "--players",
        type=int,
        default=2,
        help="Anzahl der gleichzeitig zu startenden Clients (Standard: 2)"
    )

    args = parser.parse_args()

    if args.players < 1 or args.players > 6:
        print("❌ Bitte wähle eine realistische Spieleranzahl (1-6).")
        sys.exit(1)

    start_clients(args.players)