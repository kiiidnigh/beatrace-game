# ================================================
# FILE: ui/components/invite_modal.py
# ================================================
import json
import customtkinter as ctk
from utils.ui_utils import get_centered_geometry
from services.friend_service import FriendService
from services.identity_service import IdentityService
from core.event_bus import EventBus
from core.i18n import translate


class InviteModal(ctk.CTkToplevel):
    def __init__(self, master, game_state, network):
        super().__init__(master)
        self.title(translate("social.invite_friends_title"))
        self.attributes('-topmost', True)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.geometry(get_centered_geometry(master, width=400, height=450))
        self.game_state = game_state
        self.network = network

        EventBus.subscribe("SOCIAL_FRIEND_STATUS", self._on_update)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.setup_ui()
        self.update_list()

    def destroy(self):
        EventBus.unsubscribe("SOCIAL_FRIEND_STATUS", self._on_update)
        super().destroy()

    def _on_update(self, data=None):
        self.after(0, self.update_list)

    def setup_ui(self):
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.list_frame.pack(fill="both", expand=True, padx=15, pady=15)

    def update_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        friends = FriendService.get_friends()
        if not friends:
            ctk.CTkLabel(self.list_frame, text=translate("social.no_friends"), text_color="gray").pack(pady=50)
            return

        for pub_id, f_data in friends.items():
            row = ctk.CTkFrame(self.list_frame, fg_color="#2D3436", height=40)
            row.pack(fill="x", pady=3, padx=5)

            is_online = pub_id in self.game_state.online_friends
            color = "#1DB954" if is_online else "gray"

            dot = ctk.CTkLabel(row, text="●", text_color=color, font=("Helvetica", 16))
            dot.pack(side="left", padx=(10, 5))

            ctk.CTkLabel(row, text=f_data["name"], font=("Helvetica", 14, "bold")).pack(side="left")

            btn = ctk.CTkButton(row, text=translate("social.btn_send_invite"), width=80, height=24,
                                fg_color="#3a7ebf", hover_color="#1f538d",
                                state="normal" if is_online else "disabled")

            # WICHTIG: Lambda bindet die aktuellen Werte fest an den Button
            btn.configure(command=lambda p=pub_id, b=btn: self.send_invite(p, b))
            btn.pack(side="right", padx=10)

    def send_invite(self, friend_pub_id, btn_widget):
        # 1. Unsere eigenen Daten holen
        my_identity = IdentityService.get_or_create_id()
        my_name = IdentityService.get_display_name()

        # 2. Das Paket schnüren (NEU: type = "lobby_invite")
        payload = json.dumps({
            "type": "lobby_invite",
            "sender_name": my_name,
            "sender_identity": my_identity,
            "room_code": self.game_state.room_code,
            "workspace_id": self.game_state.workspace_id
        })

        # 3. Über den PRESENCE SERVICE in den neuen Briefkasten werfen
        topic = f"beatrace/social/{friend_pub_id}/inbox"

        # Wir greifen über master (MainWindow) auf den PresenceService zu
        self.master.presence_service.client.publish(topic, payload, qos=1)

        # 4. Visuelles Feedback
        btn_widget.configure(text=translate("social.invite_sent"), fg_color="#1DB954", state="disabled")