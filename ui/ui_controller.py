# ================================================
# FILE: ui/ui_controller.py
# ================================================
import customtkinter as ctk
import json
from utils.file_utils import load_prefs, save_prefs
from core.event_bus import EventBus
from core.events import SysEvents, SocialEvents, UpdaterEvents, UIEvents, CmdEvents
from core.i18n import translate
from ui.components.custom_popup import CustomPopup
from ui.components.name_prompt_modal import NamePromptModal
from ui.components.updater_modal import UpdaterModal


class UIController:
    """
    Übernimmt die Verantwortung für systemweite Popups und Overlays.
    Entlastet das MainWindow (Single Responsibility Principle).
    """

    def __init__(self, master_window, app_core):
        self.master = master_window
        self.app_core = app_core
        self.game_state = self.app_core.game_state
        self.network = self.app_core.network

        self.warning_overlay = None
        self._is_showing_lock_warning = False

        self._setup_listeners()

    def _setup_listeners(self):
        # Native Warnungen und Blocker
        EventBus.subscribe_ui(self.master, SysEvents.FL_WARNING_SHOW, self.show_fl_warning_overlay)
        EventBus.subscribe_ui(self.master, SysEvents.FL_WARNING_HIDE, self.hide_fl_warning_overlay)
        EventBus.subscribe_ui(self.master, SysEvents.FL_MANUAL_START_BLOCKED, self.show_manual_start_warning)
        EventBus.subscribe_ui(self.master, SysEvents.FILE_CORRUPTED, self._show_file_corrupt_warning)
        EventBus.subscribe_ui(self.master, SysEvents.DAW_NOT_FOUND, self._show_daw_missing_popup)

        # NEU: Cloud Fail-Fast Popups
        EventBus.subscribe_ui(self.master, SysEvents.SYNC_ERROR, self._show_sync_error)
        EventBus.subscribe_ui(self.master, SysEvents.CLOUD_AUTH_SUCCESS, self._show_auth_success)
        EventBus.subscribe_ui(self.master, SysEvents.CLOUD_AUTH_FAILED, self._show_auth_failed)

        # Social & Updater
        EventBus.subscribe_ui(self.master, SocialEvents.INVITE_RECEIVED, self._show_invite_popup)
        EventBus.subscribe_ui(self.master, SocialEvents.FRIEND_REQUEST_RECEIVED, self._show_friend_request_popup)
        EventBus.subscribe_ui(self.master, UpdaterEvents.AVAILABLE, self._show_update_popup)
        EventBus.subscribe_ui(self.master, UIEvents.LANGUAGE_CHANGED, self._on_language_changed)

    def _on_language_changed(self, data=None):
        if self.warning_overlay and self.warning_overlay.winfo_exists():
            self.lbl_warn_title.configure(text=translate("fl_warning.title"))
            self.lbl_warn_main.configure(text=translate("fl_warning.main_text"))
            self.lbl_warn_sub.configure(text=translate("fl_warning.sub_text"))

    # --- CLOUD FEEDBACK ---
    def _show_sync_error(self, data):
        error_msg = data.get("error", "Unknown Rclone Error")
        CustomPopup(
            master=self.master,
            title=translate("errors.sync_error_title"),
            message=f"{error_msg}\n\nBitte überprüfe deine Internetverbindung und deinen Cloud-Speicherplatz.",
            icon="❌",
            btn_color="#c0392b",
            sound_type="error"
        )

    def _show_auth_success(self, data=None):
        CustomPopup(
            master=self.master,
            title=translate("errors.auth_success_title"),
            message=translate("errors.auth_success_msg"),
            icon="✅",
            btn_color="#1DB954",
            sound_type="info"
        )

    def _show_auth_failed(self, data):
        error_msg = data.get("error", "Timeout")
        CustomPopup(
            master=self.master,
            title=translate("errors.auth_failed_title"),
            message=f"Fehler: {error_msg}",
            icon="⚠️",
            btn_color="#e67e22",
            sound_type="warning"
        )

    # --- BESTEHENDE POPUPS ---
    def _show_daw_missing_popup(self, data):
        daw_name = data.get("daw_name", "DAW")
        msg = f"{daw_name} konnte nicht gefunden werden.\nBitte wähle die ausführbare Datei (.exe) manuell in den Einstellungen aus."

        CustomPopup(
            master=self.master,
            title="DAW Nicht Gefunden",
            message=msg,
            icon="🔍",
            btn_color="#e67e22",
            sound_type="warning",
            show_cancel=True,
            confirm_text="Zu den Einstellungen",
            cancel_text=translate("common.btn_cancel"),
            on_confirm_callback=self.master.open_settings
        )

    def _show_update_popup(self, data):
        latest_version = data.get("version", "")
        download_url = data.get("url", "")
        msg = translate("updater.available_msg").replace("{version}", latest_version)

        def on_confirm():
            UpdaterModal(self.master)
            EventBus.emit(CmdEvents.START_UPDATE, {"url": download_url})

        CustomPopup(
            master=self.master,
            title=translate("updater.available_title"),
            message=msg,
            icon="🚀",
            btn_color="#1DB954",
            sound_type="info",
            show_cancel=True,
            confirm_text=translate("common.yes"),
            cancel_text=translate("common.no"),
            on_confirm_callback=on_confirm
        )

    def _show_file_corrupt_warning(self, data):
        filename = data.get("file", "Unbekannt")
        CustomPopup(
            master=self.master,
            title="Datenfehler",
            message=f"Die Datei '{filename}' war beschädigt und konnte nicht geladen werden.\n\nEs wurde ein Backup erstellt und die Standardwerte wiederhergestellt.",
            icon="⚠️",
            btn_color="#e67e22",
            sound_type="warning"
        )

    def _show_friend_request_popup(self, data):
        sender_name = data.get("sender_name", "Unbekannt")
        sender_identity = data.get("sender_identity", "")

        if not sender_identity:
            return

        def accept():
            self.app_core.friend_service.add_friend(sender_name, sender_identity)
            my_identity = self.app_core.identity_service.get_or_create_id()
            my_name = self.app_core.identity_service.get_display_name()

            payload = json.dumps({
                "type": "friend_accept",
                "sender_name": my_name,
                "sender_identity": my_identity
            })

            target_pub_id = sender_identity.split("#")[0]
            EventBus.emit(CmdEvents.SEND_SOCIAL_MESSAGE, {
                "topic": f"beatrace/social/{target_pub_id}/inbox",
                "payload": payload
            })

        CustomPopup(
            master=self.master,
            title="Neue Freundschaftsanfrage",
            message=f"{sender_name} möchte dich als Freund hinzufügen!",
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

        def _proceed_to_join():
            self.game_state.room_code = code
            self.game_state.is_host = False
            self.master.show_lobby()

        def accept():
            if hasattr(self.master, 'current_view') and type(self.master.current_view).__name__ == "HomeView":
                typed_name = self.master.current_view.name_entry.get().strip()
                if typed_name:
                    self.game_state.my_name = typed_name
                    prefs = load_prefs()
                    prefs["last_username"] = typed_name
                    save_prefs(prefs)

            if not self.game_state.my_name:
                def on_name_entered(new_name):
                    if hasattr(self.master, 'current_view') and type(self.master.current_view).__name__ == "HomeView":
                        self.master.current_view.name_entry.delete(0, 'end')
                        self.master.current_view.name_entry.insert(0, new_name)
                    _proceed_to_join()

                NamePromptModal(self.master, self.game_state, on_name_entered)
                return

            _proceed_to_join()

        # KISS: Join ist jetzt immer "Auto Join", weil es keine lokalen Ordner mehr gibt!
        base_msg = translate("social.invite_popup_msg").format(player=sender, code=code)
        status_text = translate("social.invite_auto_join")

        CustomPopup(
            master=self.master,
            title=translate("social.invite_popup_title"),
            message=f"{base_msg}\n\n{status_text}",
            icon="✉️",
            btn_color="#1DB954",
            sound_type="info",
            show_cancel=True,
            confirm_text=translate("social.btn_accept"),
            cancel_text=translate("social.btn_ignore"),
            on_confirm_callback=accept
        )

    def show_fl_warning_overlay(self, data=None):
        if self.master.state() == "iconic":
            self.master.deiconify()
            self.master.lift()

        if not self.warning_overlay or not self.warning_overlay.winfo_exists():
            self.warning_overlay = ctk.CTkFrame(self.master, fg_color="#c0392b")
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

    def hide_fl_warning_overlay(self, data=None):
        if self.warning_overlay and self.warning_overlay.winfo_exists():
            self.warning_overlay.destroy()
            self.warning_overlay = None

    def show_manual_start_warning(self, data=None):
        if not self._is_showing_lock_warning:
            self._is_showing_lock_warning = True
            if self.master.state() == "iconic":
                self.master.deiconify()
            self.master.lift()

            def unlock():
                self._is_showing_lock_warning = False

            CustomPopup(
                master=self.master,
                title=translate("fl_warning.action_blocked_title"),
                message=translate("fl_warning.action_blocked_msg"),
                icon="⚠️",
                btn_color="#e67e22",
                sound_type="warning",
                on_confirm_callback=unlock,
                on_cancel_callback=unlock
            )