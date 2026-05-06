import customtkinter as ctk
import os
import subprocess
from config import settings


class FinishView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router

        self.setup_ui()

    def setup_ui(self):
        # 1. Main Container
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        # 2. Kompakter Center Block
        center_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        center_frame.pack(expand=True)

        # Großes, feierliches Banner
        ctk.CTkLabel(center_frame, text="BEATRACE BEENDET!", font=("Helvetica", 48, "bold"), text_color="#1DB954").pack(
            pady=(0, 20))

        ctk.CTkLabel(center_frame, text="Alle Spieler haben ihre Zeit aufgebraucht oder abgegeben.",
                     font=("Helvetica", 18), text_color="gray").pack(pady=(0, 40))

        # Finale Statistik
        stats_frame = ctk.CTkFrame(center_frame, fg_color="#1e1e1e")
        stats_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(stats_frame, text="Teilnehmer:", font=("Helvetica", 16, "bold")).pack(pady=(15, 5))

        for player in self.game_state.players:
            ctk.CTkLabel(stats_frame, text=f"✅ {player}", font=("Helvetica", 18), text_color="white").pack(pady=5)

        # Platzhalter für einen sauberen Abstand nach unten
        ctk.CTkLabel(stats_frame, text="", height=5).pack()

        # Aktions-Buttons
        btn_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        btn_frame.pack(pady=40)

        # Öffnet den Datei-Explorer direkt beim finalen Projekt
        btn_open = ctk.CTkButton(btn_frame, text="FINALES PROJEKT ÖFFNEN", height=50, width=250,
                                 font=("Helvetica", 14, "bold"),
                                 fg_color="#8e44ad", hover_color="#9b59b6", command=self.open_project_folder)
        btn_open.pack(side="left", padx=10)

        btn_home = ctk.CTkButton(btn_frame, text="ZURÜCK ZUM HAUPTMENÜ", height=50, width=250,
                                 font=("Helvetica", 14, "bold"),
                                 fg_color="#636E72", hover_color="#2D3436", command=self.go_home)
        btn_home.pack(side="left", padx=10)

    def open_project_folder(self):
        path = self.game_state.local_project_path
        if os.path.exists(path):
            # Öffnet den Windows Explorer und markiert direkt die ZIP-Datei
            subprocess.Popen(r'explorer /select,"{}"'.format(os.path.abspath(path)))
        else:
            # Fallback, falls nur der Ordner existiert
            folder = self.game_state.local_drive_folder
            if os.path.exists(folder):
                os.startfile(folder)

    def go_home(self):
        # Das Netzwerk sicher trennen, bevor wir ins Menü gehen
        if self.network:
            self.network.disconnect()
        self.router.show_home()