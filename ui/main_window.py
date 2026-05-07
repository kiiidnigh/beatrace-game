import customtkinter as ctk
import tkinter.messagebox as messagebox
import threading
import time
from core.game_state import GameState
from network.mqtt_client import NetworkManager
from services.updater_service import UpdaterService
from services.telemetry_service import TelemetryService

from utils.process import is_fl_running, kill_all_fl_instances

from ui.views.home_view import HomeView
from ui.views.host_view import HostView
from ui.views.join_view import JoinView
from ui.views.lobby_view import LobbyView
from ui.views.game_view import GameView


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Beatrace Manager")

        # --- ADAPTIVES LAYOUT ---
        self.geometry("1000x700")
        self.minsize(800, 600)
        ctk.set_appearance_mode("dark")
        self._setup_toolbar()

        self.game_state = GameState()
        self.network = NetworkManager()

        self.current_view = None

        # --- Globaler FL Studio Wachhund ---
        self.fl_monitor_state = "WAITING_FOR_CLOSE"
        self.warning_overlay = None
        self._is_showing_lock_warning = False
        self._monitor_running = True

        self.start_global_fl_monitor()

        self.show_home()

        self.updater = UpdaterService(self)
        self.after(1000, self.updater.check_for_updates)

    def _setup_toolbar(self):
        """Erstellt eine fixe Toolbar am oberen Bildschirmrand."""
        self.toolbar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#111111")
        self.toolbar.pack(side="top", fill="x")

        btn_help = ctk.CTkButton(self.toolbar, text="Bug melden", width=100, height=24,
                                 fg_color="transparent", hover_color="#c0392b", text_color="lightgray",
                                 command=self._send_bug_report)
        btn_help.pack(side="right", padx=10, pady=3)

    def _send_bug_report(self):
        """Öffnet das Textfenster für Bug-Reports."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Bug melden")
        dialog.geometry("500x400")
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)

        ctk.CTkLabel(dialog, text="Was genau ist schief gelaufen?", font=("Helvetica", 16, "bold")).pack(pady=(20, 10))

        textbox = ctk.CTkTextbox(dialog, width=450, height=200)
        textbox.pack(pady=10)

        ctk.CTkLabel(dialog, text="Systemdaten und der aktuelle Log werden automatisch angehängt.",
                     text_color="gray", font=("Helvetica", 12)).pack(pady=(0, 10))

        def submit():
            user_msg = textbox.get("1.0", "end-1c").strip()
            if not user_msg:
                user_msg = "Keine Beschreibung angegeben."

            btn_submit.configure(state="disabled", text="Sende...")

            def on_done(success):
                if dialog.winfo_exists():
                    dialog.destroy()
                if success:
                    messagebox.showinfo("Gesendet", "Vielen Dank! Der Bug Report wurde erfolgreich übermittelt.")
                else:
                    messagebox.showerror("Fehler",
                                         "Report konnte nicht gesendet werden. Überprüfe deine Internetverbindung.")

            TelemetryService.send_crash_report(user_message=user_msg,
                                               callback=lambda s: self.after(0, lambda: on_done(s)))

        btn_submit = ctk.CTkButton(dialog, text="Report Senden", fg_color="#c0392b", hover_color="#e74c3c",
                                   command=submit)
        btn_submit.pack(pady=10)

    # --- WACHHUND LOGIK ---
    def start_global_fl_monitor(self):
        def loop():
            while self._monitor_running:
                if self.fl_monitor_state in ["GAME_RUNNING", "FINISH"]:
                    self.after(0, self.hide_fl_warning_overlay)
                    time.sleep(1.0)

                elif self.fl_monitor_state == "WAITING_FOR_CLOSE":
                    if is_fl_running():
                        self.after(0, self.show_fl_warning_overlay)
                    else:
                        self.fl_monitor_state = "LOCKED"
                        self.after(0, self.hide_fl_warning_overlay)
                    time.sleep(0.5)

                elif self.fl_monitor_state == "LOCKED":
                    if kill_all_fl_instances():
                        self.after(0, self.show_manual_start_warning)
                    time.sleep(0.2)

        threading.Thread(target=loop, daemon=True).start()

    def show_fl_warning_overlay(self):
        if not self.warning_overlay or not self.warning_overlay.winfo_exists():
            self.warning_overlay = ctk.CTkFrame(self, fg_color="#c0392b")
            self.warning_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.warning_overlay.lift()

            center_frame = ctk.CTkFrame(self.warning_overlay, fg_color="transparent")
            center_frame.pack(expand=True)

            ctk.CTkLabel(center_frame, text="⚠️ ACHTUNG", font=("Helvetica", 36, "bold"),
                         text_color="white").pack(pady=(0, 20))
            ctk.CTkLabel(center_frame,
                         text="Beatrace kann erst genutzt werden,\nwenn FL Studio geschlossen ist!",
                         font=("Helvetica", 20, "bold"), text_color="white").pack(pady=10)
            ctk.CTkLabel(center_frame,
                         text="(Bitte speichere dein Projekt und schließe FL Studio.\nDieser Bildschirm verschwindet dann automatisch.)",
                         font=("Helvetica", 14), text_color="lightgray").pack(pady=20)

    def hide_fl_warning_overlay(self):
        if self.warning_overlay and self.warning_overlay.winfo_exists():
            self.warning_overlay.destroy()
            self.warning_overlay = None

    def show_manual_start_warning(self):
        if not self._is_showing_lock_warning:
            self._is_showing_lock_warning = True
            messagebox.showwarning(
                "Aktion blockiert",
                "Beatrace überwacht gerade das System!\n\nFL Studio kann nicht manuell gestartet werden, solange du dich im Beatrace-Menü befindest.\n\nDas Programm wird FL Studio vollautomatisch für dich öffnen, sobald du an der Reihe bist."
            )
            self._is_showing_lock_warning = False

    # --- FENSTER SCHLIESSEN (Clean Exit) ---
    def destroy(self):
        self._monitor_running = False
        super().destroy()

    # --- DIE ROUTEN ---
    def switch_view(self, view_class, **kwargs):
        if self.current_view:
            self.current_view.destroy()
        self.current_view = view_class(self, self.game_state, self.network, **kwargs)
        self.current_view.pack(fill="both", expand=True)

    def show_home(self):
        if self.fl_monitor_state in ["GAME_RUNNING", "FINISH"]:
            self.fl_monitor_state = "WAITING_FOR_CLOSE"
        self.switch_view(HomeView, router=self)

    def show_host(self):
        self.switch_view(HostView, router=self)

    def show_join(self):
        self.switch_view(JoinView, router=self)

    def show_lobby(self):
        self.switch_view(LobbyView, router=self)

    def start_game(self):
        self.fl_monitor_state = "GAME_RUNNING"
        self.switch_view(GameView, router=self)

    def show_finish(self):
        self.fl_monitor_state = "FINISH"
        from ui.views.finish_view import FinishView
        self.switch_view(FinishView, router=self)