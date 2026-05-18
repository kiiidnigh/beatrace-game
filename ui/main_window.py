# ================================================
# FILE: ui/main_window.py
# ================================================
import customtkinter as ctk

from core.event_bus import EventBus
from core.i18n import translate
from config.settings import VERSION

from ui.views.home_view import HomeView
from ui.views.host_view import HostView
from ui.views.join_view import JoinView
from ui.views.lobby_view import LobbyView
from ui.views.game_view import GameView
from ui.views.setup_view import SetupView
from ui.components.custom_popup import CustomPopup

from ui.ui_controller import UIController


class MainWindow(ctk.CTk):
    def __init__(self, app_core):
        super().__init__()

        self.app_core = app_core
        self.game_state = self.app_core.game_state
        self.network = self.app_core.network
        self.system_monitor = self.app_core.system_monitor
        self.lobby_service = self.app_core.lobby_service

        self.title(f"Beatrace Client {VERSION}")
        self.geometry("1000x700")
        self.minsize(800, 600)
        ctk.set_appearance_mode("dark")
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._setup_toolbar()

        self.current_view = None
        self.ui_controller = UIController(self, self.app_core)

        self._setup_event_listeners()

        saved_name = self.app_core.identity_service.get_display_name()
        if not saved_name:
            self.show_setup()
        else:
            self.game_state.my_name = saved_name
            self.show_home()

        self.after(1000, lambda: EventBus.emit("CMD_CHECK_FOR_UPDATES"))

    def _setup_event_listeners(self):
        EventBus.subscribe("SOCIAL_FRIEND_STATUS", lambda d: self.after(0, lambda: self.game_state.set_friend_online(
            d["public_id"], d["status"] == "online")))

        EventBus.subscribe("CMD_RETURN_TO_LOBBY", lambda d: self.after(0, self._handle_return_to_lobby))
        EventBus.subscribe("STATE_ANALYSIS_COMPLETE", lambda d: self.after(0, self.show_finish))
        EventBus.subscribe("LANGUAGE_CHANGED", lambda d: self.after(0, self._on_language_changed))

    # --- ZENTRALES POPUP MANAGEMENT (Keine Duplikate mehr möglich) ---
    def open_settings(self):
        if hasattr(self, "_settings_modal") and self._settings_modal.winfo_exists():
            self._settings_modal.focus()
        else:
            from ui.components.settings_modal import SettingsModal
            self._settings_modal = SettingsModal(self)

    def open_friends(self):
        if hasattr(self, "_friends_modal") and self._friends_modal.winfo_exists():
            self._friends_modal.focus()
        else:
            from ui.components.friends_modal import FriendsModal
            self._friends_modal = FriendsModal(self, self.game_state)

    def open_invite(self):
        if hasattr(self, "_invite_modal") and self._invite_modal.winfo_exists():
            self._invite_modal.focus()
        else:
            from ui.components.invite_modal import InviteModal
            self._invite_modal = InviteModal(self, self.game_state, self.network)

    def open_bug_report(self):
        if hasattr(self, "_bug_modal") and self._bug_modal.winfo_exists():
            self._bug_modal.focus()
        else:
            from ui.components.bug_report_modal import BugReportModal
            self._bug_modal = BugReportModal(self)

    # ------------------------------------------------------------------

    def _handle_return_to_lobby(self):
        if self.game_state.room_code:
            self.app_core.workspace_service.cleanup_match_workspace(self.game_state.room_code)

        self.game_state.prepare_next_match()
        self.app_core.workspace_service.setup_match_workspace(self.game_state)

        self.show_lobby()

        if self.game_state.is_host:
            self.network.send_signal("RETURN_TO_LOBBY")

    def _on_closing(self):
        if self.network.is_connected:
            CustomPopup(
                master=self,
                title="Beenden?",
                message="Willst du Beatrace wirklich beenden?\nDie aktuelle Sitzung wird für alle abgebrochen.",
                icon="⚠️",
                btn_color="#e67e22",
                sound_type="warning",
                show_cancel=True,
                confirm_text=translate("common.yes"),
                cancel_text=translate("common.no"),
                on_confirm_callback=self._force_quit
            )
        else:
            self._force_quit()

    def _force_quit(self):
        if self.network.is_connected:
            if self.game_state.is_host:
                self.network.send_signal("LOBBY_CLOSED")
            else:
                self.network.send_signal("CLIENT_LEAVE")
        self.destroy()

    def _on_language_changed(self):
        self.btn_help.configure(text=translate("bug_report.btn_report"))

    def _setup_toolbar(self):
        self.toolbar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#111111")
        self.toolbar.pack(side="top", fill="x")

        self.btn_help = ctk.CTkButton(
            self.toolbar, text=translate("bug_report.btn_report"), width=100, height=24,
            fg_color="transparent", hover_color="#c0392b", text_color="lightgray",
            command=self.open_bug_report
        )
        self.btn_help.pack(side="right", padx=10, pady=3)

    def switch_view(self, view_class, **kwargs):
        self.lobby_service.stop()
        if self.current_view:
            self.current_view.destroy()
        self.current_view = view_class(self, self.game_state, self.network, **kwargs)
        self.current_view.pack(fill="both", expand=True)

    def show_setup(self):
        self.system_monitor.set_state("WAITING_FOR_CLOSE")
        self.switch_view(SetupView, router=self)

    def show_home(self):
        self.system_monitor.set_state("WAITING_FOR_CLOSE")
        self.switch_view(HomeView, router=self)

    def show_host(self):
        self.switch_view(HostView, router=self)

    def show_join(self):
        self.switch_view(JoinView, router=self)

    def show_lobby(self):
        self.switch_view(LobbyView, router=self)
        self.lobby_service.start()

    def start_game(self):
        self.system_monitor.set_state("GAME_RUNNING")
        self.switch_view(GameView, router=self)

    def show_finish(self):
        self.system_monitor.set_state("FINISH")
        from ui.views.finish_view import FinishView
        self.switch_view(FinishView, router=self)