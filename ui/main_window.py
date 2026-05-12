# ================================================
# FILE: ui/main_window.py
# ================================================
import customtkinter as ctk
import json

from network.mqtt_client import NetworkManager
from services.updater_service import UpdaterService
from services.telemetry_service import TelemetryService
from services.system_monitor_service import SystemMonitorService
from services.handshake_service import HandshakeService
from services.discord_service import DiscordService
from services.presence_service import PresenceService
from services.workspace_service import WorkspaceService
from services.identity_service import IdentityService
from utils.file_utils import load_prefs, save_prefs
from utils.ui_utils import get_centered_geometry
from core.event_bus import EventBus
from core.i18n import translate
from core.game_state import GameState
from config.settings import VERSION

from ui.views.home_view import HomeView
from ui.views.host_view import HostView
from ui.views.join_view import JoinView
from ui.views.lobby_view import LobbyView
from ui.views.game_view import GameView
from ui.views.setup_view import SetupView
from ui.components.custom_popup import CustomPopup


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Beatrace Client {VERSION}")
        self.geometry("1000x700")
        self.minsize(800, 600)
        ctk.set_appearance_mode("dark")
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._setup_toolbar()

        self.game_state = GameState()
        self.network = NetworkManager()
        self.current_view = None

        self.warning_overlay = None
        self._is_showing_lock_warning = False

        self._setup_event_listeners()

        self.system_monitor = SystemMonitorService()
        self.system_monitor.start()

        self.handshake_service = HandshakeService()
        self.discord_service = DiscordService()

        # Start des Social Netzwerks
        self.presence_service = PresenceService()
        self.presence_service.start()

        # --- NEU: Routing Logik für First-Time Setup ---
        saved_name = IdentityService.get_display_name()
        if not saved_name:
            # Erster Start: Profil existiert noch nicht
            self.show_setup()
        else:
            # Wiederkehrender Spieler: Direkt Name laden und ab ins Hauptmenü
            self.game_state.my_name = saved_name
            self.show_home()

        self.updater = UpdaterService(self)
        self.after(1000, self.updater.check_for_updates)

    def _setup_event_listeners(self):
        EventBus.subscribe("SYS_FL_WARNING_SHOW", lambda d: self.after(0, self.show_fl_warning_overlay))
        EventBus.subscribe("SYS_FL_WARNING_HIDE", lambda d: self.after(0, self.hide_fl_warning_overlay))
        EventBus.subscribe("SYS_FL_MANUAL_START_BLOCKED", lambda d: self.after(0, self.show_manual_start_warning))
        EventBus.subscribe("LANGUAGE_CHANGED", lambda d: self.after(0, self._on_language_changed))

        # Social Events abfangen
        EventBus.subscribe("SOCIAL_FRIEND_STATUS", lambda d: self.after(0, lambda: self.game_state.set_friend_online(d["public_id"], d["status"] == "online")))
        EventBus.subscribe("SOCIAL_INVITE_RECEIVED", lambda d: self.after(0, lambda: self._show_invite_popup(d)))
        EventBus.subscribe("SOCIAL_FRIEND_REQUEST_RECEIVED", lambda d: self.after(0, lambda: self._show_friend_request_popup(d)))

    def _show_friend_request_popup(self, data):
        sender_name = data.get("sender_name", "Unbekannt")
        sender_identity = data.get("sender_identity", "")

        if not sender_identity:
            return

        def accept():
            # 1. Lokal als Freund speichern
            from services.friend_service import FriendService
            FriendService.add_friend(sender_name, sender_identity)

            # 2. Dem anderen antworten: "Angenommen!"
            my_identity = IdentityService.get_or_create_id()
            my_name = IdentityService.get_display_name()

            payload = json.dumps({
                "type": "friend_accept",
                "sender_name": my_name,
                "sender_identity": my_identity
            })
            target_pub_id = sender_identity.split("#")[0]
            self.presence_service.client.publish(f"beatrace/social/{target_pub_id}/inbox", payload, qos=1)

        msg = f"{sender_name} möchte dich als Freund hinzufügen!"

        CustomPopup(
            master=self,
            title="Neue Freundschaftsanfrage",
            message=msg,
            icon="🤝",
            btn_color="#1DB954",
            sound_type="info",
            show_cancel=True,
            confirm_text="Annehmen",
            cancel_text="Ablehnen",
            on_confirm_callback=accept
        )

    def _show_invite_popup(self, data):
        if self.network.is_connected:
            return

        sender = data.get("sender_name", translate("common.unknown"))
        code = data.get("room_code", "")
        invite_workspace_id = data.get("workspace_id", "")

        auto_join_path = WorkspaceService.get_auto_join_path(invite_workspace_id)

        # Ausgelagerte Logik für den erfolgreichen Join
        def _proceed_to_join():
            self.game_state.room_code = code
            self.game_state.is_host = False

            if auto_join_path:
                self.game_state.local_drive_folder = auto_join_path
                self.show_lobby()
            else:
                self.show_join()

        def accept():
            # 1. Namen aus dem Textfeld ziehen (falls wir im HomeView sind)
            if hasattr(self, 'current_view') and type(self.current_view).__name__ == "HomeView":
                typed_name = self.current_view.name_entry.get().strip()
                if typed_name:
                    self.game_state.my_name = typed_name
                    prefs = load_prefs()
                    prefs["last_username"] = typed_name
                    save_prefs(prefs)

            # 2. Eigenes, sauber zentriertes Modal bauen, falls der Name fehlt
            if not self.game_state.my_name:
                dialog = ctk.CTkToplevel(self)
                dialog.title(translate("social.invite_name_title"))
                dialog.attributes('-topmost', True)
                dialog.resizable(False, False)
                dialog.transient(self)
                dialog.grab_set()

                # Exakt über dem MainWindow zentrieren!
                dialog.geometry(get_centered_geometry(self, width=350, height=200))

                ctk.CTkLabel(dialog, text=translate("social.invite_name_prompt"), font=("Helvetica", 14, "bold")).pack(
                    pady=(20, 10))

                entry = ctk.CTkEntry(dialog, width=200, justify="center")
                entry.pack(pady=10)
                entry.focus()

                def on_submit():
                    new_name = entry.get().strip()
                    if new_name:
                        self.game_state.my_name = new_name
                        prefs = load_prefs()
                        prefs["last_username"] = new_name
                        save_prefs(prefs)

                        # Optische Kosmetik: Textfeld auffüllen
                        if hasattr(self, 'current_view') and type(self.current_view).__name__ == "HomeView":
                            self.current_view.name_entry.delete(0, 'end')
                            self.current_view.name_entry.insert(0, new_name)

                        dialog.destroy()
                        _proceed_to_join()

                btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
                btn_frame.pack(pady=15)

                ctk.CTkButton(btn_frame, text=translate("common.btn_save"), width=100,
                              fg_color="#1DB954", hover_color="#14833b", command=on_submit).pack(side="left", padx=5)
                ctk.CTkButton(btn_frame, text=translate("common.btn_cancel"), width=100,
                              fg_color="#c0392b", hover_color="#e74c3c", command=dialog.destroy).pack(side="left",
                                                                                                      padx=5)
                return

            # 3. Wenn der Name schon da war, direkt weiter
            _proceed_to_join()

        # UI für die ursprüngliche Einladung aufbauen
        base_msg = translate("social.invite_popup_msg").format(player=sender, code=code)

        if auto_join_path:
            status_text = translate("social.invite_auto_join")
            btn_color = "#1DB954"
        else:
            status_text = translate("social.invite_manual_join")
            btn_color = "#e67e22"

        full_msg = f"{base_msg}\n\n{status_text}"

        CustomPopup(
            master=self,
            title=translate("social.invite_popup_title"),
            message=full_msg,
            icon="✉️",
            btn_color=btn_color,
            sound_type="info",
            show_cancel=True,
            confirm_text=translate("social.btn_accept"),
            cancel_text=translate("social.btn_ignore"),
            on_confirm_callback=accept
        )

    def _on_closing(self):
        if self.network.is_connected:
            def confirm_quit():
                self._force_quit()

            CustomPopup(
                master=self,
                title="Beenden?",
                message=f"Willst du Beatrace wirklich beenden?\nDie aktuelle Sitzung wird für alle abgebrochen.",
                icon="⚠️",
                btn_color="#e67e22",
                sound_type="warning",
                show_cancel=True,
                confirm_text=translate("common.yes"),
                cancel_text=translate("common.no"),
                on_confirm_callback=confirm_quit
            )
        else:
            self._force_quit()

    def _force_quit(self):
        if self.network.is_connected:
            if self.game_state.is_host:
                self.network.send_signal("LOBBY_CLOSED")
            else:
                self.network.send_signal("CLIENT_LEAVE")
            self.network.disconnect()

        self.destroy()

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
        ctk.CTkLabel(dialog, text=translate("bug_report.info"), text_color="gray", font=("Helvetica", 12)).pack(
            pady=(0, 10))

        def submit():
            user_msg = textbox.get("1.0", "end-1c").strip()
            if not user_msg:
                user_msg = translate("bug_report.empty_desc")
            btn_submit.configure(state="disabled", text=translate("bug_report.btn_sending"))

            def on_done(success):
                if dialog.winfo_exists():
                    dialog.destroy()
                if success:
                    CustomPopup(master=self, title=translate("bug_report.success_title"),
                                message=translate("bug_report.success_msg"),
                                icon="✅", btn_color="#1DB954", sound_type="ok")
                else:
                    CustomPopup(master=self, title=translate("bug_report.error_title"),
                                message=translate("bug_report.error_msg"),
                                icon="❌", btn_color="#c0392b", sound_type="error")

            TelemetryService.send_crash_report(user_message=user_msg,
                                               callback=lambda s: self.after(0, lambda: on_done(s)))

        btn_submit = ctk.CTkButton(dialog, text=translate("bug_report.btn_send"), fg_color="#c0392b",
                                   hover_color="#e74c3c", command=submit)
        btn_submit.pack(pady=10)

    def show_fl_warning_overlay(self):
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
            self.lbl_warn_sub = ctk.CTkLabel(center_frame, text=translate("fl_warning.sub_text"),
                                             font=("Helvetica", 14), text_color="lightgray")
            self.lbl_warn_sub.pack(pady=20)

    def hide_fl_warning_overlay(self):
        if self.warning_overlay and self.warning_overlay.winfo_exists():
            self.warning_overlay.destroy()
            self.warning_overlay = None

    def show_manual_start_warning(self):
        if not self._is_showing_lock_warning:
            self._is_showing_lock_warning = True
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
                on_confirm_callback=unlock,
                on_cancel_callback=unlock
            )

    def destroy(self):
        self.system_monitor.stop()
        self.handshake_service.cleanup()
        self.presence_service.stop()
        if hasattr(self, 'discord_service'):
            self.discord_service.cleanup()
        super().destroy()

    def switch_view(self, view_class, **kwargs):
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

    def start_game(self):
        self.system_monitor.set_state("GAME_RUNNING")
        self.switch_view(GameView, router=self)

    def show_finish(self):
        self.system_monitor.set_state("FINISH")
        from ui.views.finish_view import FinishView
        self.switch_view(FinishView, router=self)