import customtkinter as ctk
import os
import subprocess


class FinishView(ctk.CTkFrame):
    def __init__(self, master, game_state, network, router):
        super().__init__(master)
        self.game_state = game_state
        self.network = network
        self.router = router

        # DRY: Wir nutzen die bereits vom MatchController gecachten Stats!
        # Kein doppeltes Entpacken oder Rechnen mehr nötig.
        self.match_stats = self.game_state.match_stats

        self.setup_ui()

    def setup_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # 1. Header
        header_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(header_frame, text="BEATRACE BEENDET!", font=("Helvetica", 42, "bold"),
                     text_color="#1DB954").pack()
        ctk.CTkLabel(header_frame, text="Alle Spieler haben ihre Zeit aufgebraucht oder abgegeben.",
                     font=("Helvetica", 16), text_color="gray").pack()

        # 2. Split Content (Beide Seiten scrollbar)
        content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)

        # ==========================================
        # LINKE SEITE: Projekt Daten (Scrollable)
        # ==========================================
        left_panel = ctk.CTkScrollableFrame(content_frame, fg_color="#1e1e1e", width=400, corner_radius=10)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(left_panel, text="Projekt Daten", font=("Helvetica", 20, "bold")).pack(pady=(15, 15))

        # Dynamische Generierung der Projekt-Fakten Karten
        project_data = self.match_stats.get("project_data", {})

        # Dateigröße als manuelle Karte
        self._create_stat_row(left_panel, "💾 Dateigröße", self.match_stats.get("file_size", "0.00 MB"))

        if not project_data:
            ctk.CTkLabel(left_panel, text="Keine Daten extrahiert.", text_color="gray").pack(pady=20)
        else:
            for title, value in project_data.items():
                self._create_stat_row(left_panel, title, value)

        # Version Info ganz unten im Scroll-Bereich
        ctk.CTkLabel(left_panel, text=f"FL Studio Version: {self.match_stats.get('fl_version', 'Unbekannt')}",
                     font=("Helvetica", 12), text_color="gray").pack(pady=(20, 10))

        # ==========================================
        # RECHTE SEITE: Awards (Scrollable)
        # ==========================================
        right_panel = ctk.CTkScrollableFrame(content_frame, fg_color="#2D3436", width=400, corner_radius=10)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        ctk.CTkLabel(right_panel, text="🏆 Match Awards", font=("Helvetica", 20, "bold"), text_color="#f1c40f").pack(
            pady=(15, 15))

        awards = self.match_stats.get("awards", {})
        if not awards:
            ctk.CTkLabel(right_panel, text="Nicht genug Daten für Auszeichnungen gesammelt.", font=("Helvetica", 14),
                         text_color="gray").pack(expand=True, pady=50)
        else:
            for title, winner in awards.items():
                award_card = ctk.CTkFrame(right_panel, fg_color="#1e1e1e", corner_radius=8)
                award_card.pack(fill="x", padx=15, pady=8)

                ctk.CTkLabel(award_card, text=title, font=("Helvetica", 16, "bold"), text_color="#1DB954").pack(
                    anchor="w", padx=15, pady=(10, 0))
                ctk.CTkLabel(award_card, text=winner, font=("Helvetica", 14), text_color="white").pack(anchor="w",
                                                                                                       padx=15,
                                                                                                       pady=(0, 10))

        # 3. Footer / Aktionen
        btn_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        btn_frame.pack(pady=(20, 0))

        btn_open = ctk.CTkButton(btn_frame, text="FINALES PROJEKT ÖFFNEN", height=50, width=250,
                                 font=("Helvetica", 14, "bold"),
                                 fg_color="#8e44ad", hover_color="#9b59b6", command=self.open_project_folder)
        btn_open.pack(side="left", padx=10)

        btn_home = ctk.CTkButton(btn_frame, text="ZURÜCK ZUM HAUPTMENÜ", height=50, width=250,
                                 font=("Helvetica", 14, "bold"),
                                 fg_color="#636E72", hover_color="#2D3436", command=self.go_home)
        btn_home.pack(side="left", padx=10)

    def _create_stat_row(self, parent, title, value):
        """Hilfsfunktion für flache, platzsparende Karten in der Liste."""
        box = ctk.CTkFrame(parent, fg_color="#2D3436", corner_radius=8, height=60)
        box.pack(fill="x", padx=15, pady=6)
        box.pack_propagate(False)

        ctk.CTkLabel(box, text=title, font=("Helvetica", 14), text_color="gray").pack(side="left", padx=15)
        ctk.CTkLabel(box, text=str(value), font=("Helvetica", 16, "bold"), text_color="white").pack(side="right",
                                                                                                    padx=15)

    def open_project_folder(self):
        path = self.game_state.local_project_path
        if os.path.exists(path):
            subprocess.Popen(r'explorer /select,"{}"'.format(os.path.abspath(path)))
        else:
            folder = self.game_state.local_drive_folder
            if os.path.exists(folder):
                os.startfile(folder)

    def go_home(self):
        if self.network:
            self.network.disconnect()
        self.router.show_home()