# ================================================
# FILE: ui/main_window.py
# ================================================
import customtkinter as ctk

from config import settings
from core.game_state import GameState
from network.mqtt_client import NetworkManager
from services.updater_service import UpdaterService
from services.telemetry_service import TelemetryService
from services.system_monitor_service import SystemMonitorService
from utils.ui_utils import get_centered_geometry
from core.event_bus import EventBus
from core.i18n import translate

from ui.views.home_view import HomeView
from ui.views.host_view import HostView
from ui.views.join_view import JoinView
from ui.views.lobby_view import LobbyView
from ui.views.game_view import GameView
from ui.components.custom_popup import CustomPopup


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Beatrace Client")
        self.geometry("1000x700")
        self.minsize(800, 600)
        ctk.set_appearance_mode("dark")

        self._setup_toolbar()

        self.game_state = GameState()
        self.network = NetworkManager()
        self.current_view = None

        self.system_monitor = SystemMonitorService()
        self.system_monitor.start()

        self.warning_overlay = None
        self._is_showing_lock_warning = False

        self._setup_event_listeners()

        self.show_home()

        self.updater = UpdaterService(self)
        self.after(1000, self.updater.check_for_updates)

    def _setup_event_listeners(self):
        EventBus.subscribe("SYS_FL_WARNING_SHOW", lambda d: self.after(0, self.show_fl_warning_overlay))
        EventBus.subscribe("SYS_FL_WARNING_HIDE", lambda d: self.after(0, self.hide_fl_warning_overlay))
        EventBus.subscribe("SYS_FL_MANUAL_START_BLOCKED", lambda d: self.after(0, self.show_manual_start_warning))
        EventBus.subscribe("LANGUAGE_CHANGED", lambda d: self.after(0, self._on_language_changed))

    def _on_language_changed(self):
        self.btn_help.configure(text=translate("bug_report.btn_report"))

        if self.warning_overlay and self.warning_overlay.winfo_exists():
            self.lbl_warn_title.configure(text=translate("fl_warning.title"))
            self.lbl_warn_main.configure(text=translate("fl_warning.main_text"))
            self.lbl_warn_sub.configure(text=translate("fl_warning.sub_text"))

    def _setup_toolbar(self):
        self.toolbar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#111111")
        self.toolbar.pack(side="top", fill="x")

        self.btn_help = ctk.CTkButton(
            self.toolbar, text=translate("bug_report.btn_report"), width=100, height=24,
            fg_color="transparent", hover_color="#c0392b", text_color="lightgray",
            command=self._send_bug_report
        )
        self.btn_help.pack(side="right", padx=10, pady=3)

    def _send_bug_report(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title(translate("bug_report.title"))
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)

        dialog.transient(self)
        dialog.grab_set()

        dialog.geometry(get_centered_geometry(self, width=500, height=400))

        ctk.CTkLabel(dialog, text=translate("bug_report.question"), font=("Helvetica", 16, "bold")).pack(pady=(20, 10))

        textbox = ctk.CTkTextbox(dialog, width=450, height=200)
        textbox.pack(pady=10)

        ctk.CTkLabel(dialog, text=translate("bug_report.info"),
                     text_color="gray", font=("Helvetica", 12)).pack(pady=(0, 10))

        def submit():
            user_msg = textbox.get("1.0", "end-1c").strip()
            if not user_msg:
                user_msg = translate("bug_report.empty_desc")

            btn_submit.configure(state="disabled", text=translate("bug_report.btn_sending"))

            def on_done(success):
                if dialog.winfo_exists():
                    dialog.destroy()

                if success:
                    CustomPopup(
                        master=self,
                        title=translate("bug_report.success_title"),
                        message=translate("bug_report.success_msg"),
                        icon="✅",
                        btn_color="#1DB954",
                        sound_type="ok"
                    )
                else:
                    CustomPopup(
                        master=self,
                        title=translate("bug_report.error_title"),
                        message=translate("bug_report.error_msg"),
                        icon="❌",
                        btn_color="#c0392b",
                        sound_type="error"
                    )

            TelemetryService.send_crash_report(
                user_message=user_msg,
                callback=lambda s: self.after(0, lambda: on_done(s))
            )

        btn_submit = ctk.CTkButton(dialog, text=translate("bug_report.btn_send"), fg_color="#c0392b",
                                   hover_color="#e74c3c",
                                   command=submit)
        btn_submit.pack(pady=10)

    def show_fl_warning_overlay(self):
        # FIX: Verhindert, dass das Overlay in einem minimierten Fenster gefangen bleibt
        if self.state() == "iconic":
            self.deiconify()
            self.lift()

        if not self.warning_overlay or not self.warning_overlay.winfo_exists():
            self.warning_overlay = ctk.CTkFrame(self, fg_color="#c0392b")
            self.warning_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.warning_overlay.lift()

            center_frame = ctk.CTkFrame(self.warning_overlay, fg_color="transparent")
            center_frame.pack(expand=True)

            self.lbl_warn_title = ctk.CTkLabel(center_frame, text=translate("fl_warning.title"),
                                               font=("Helvetica", 36, "bold"), text_color="white")
            self.lbl_warn_title.pack(pady=(0, 20))

            self.lbl_warn_main = ctk.CTkLabel(center_frame, text=translate("fl_warning.main_text"),
                                              font=("Helvetica", 20, "bold"), text_color="white")
            self.lbl_warn_main.pack(pady=10)

            self.lbl_warn_sub = ctk.CTkLabel(center_frame,
                                             text=translate("fl_warning.sub_text"),
                                             font=("Helvetica", 14), text_color="lightgray")
            self.lbl_warn_sub.pack(pady=20)

    def hide_fl_warning_overlay(self):
        if self.warning_overlay and self.warning_overlay.winfo_exists():
            self.warning_overlay.destroy()
            self.warning_overlay = None

    def show_manual_start_warning(self):
        if not self._is_showing_lock_warning:
            self._is_showing_lock_warning = True

            # FIX: Wenn die App minimiert in der Taskleiste liegt, zwingen wir sie auf
            # den Bildschirm, BEVOR wir das modale Dialogfenster mit grab_set() öffnen.
            if self.state() == "iconic":
                self.deiconify()

            self.lift()

            def unlock():
                self._is_showing_lock_warning = False

            CustomPopup(
                master=self,
                title=translate("fl_warning.action_blocked_title"),
                message=translate("fl_warning.action_blocked_msg"),
                icon="⚠️",
                btn_color="#e67e22",
                sound_type="warning",
                on_close_callback=unlock
            )

    def destroy(self):
        self.system_monitor.stop()
        super().destroy()

    def switch_view(self, view_class, **kwargs):
        if self.current_view:
            self.current_view.destroy()
        self.current_view = view_class(self, self.game_state, self.network, **kwargs)
        self.current_view.pack(fill="both", expand=True)

    def show_home(self):
        self.system_monitor.set_state("WAITING_FOR_CLOSE")
        self.switch_view(HomeView, router=self)

    def show_host(self):
        self.switch_view(HostView, router=self)

    def show_join(self):
        self.switch_view(JoinView, router=self)

    def show_lobby(self):
        self.switch_view(LobbyView, router=self)

    def start_game(self):
        self.system_monitor.set_state("GAME_RUNNING")
        self.switch_view(GameView, router=self)

    def show_finish(self):
        self.system_monitor.set_state("FINISH")
        from ui.views.finish_view import FinishView
        self.switch_view(FinishView, router=self)