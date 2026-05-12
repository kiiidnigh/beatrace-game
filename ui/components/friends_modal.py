# ================================================
# FILE: ui/components/friends_modal.py
# ================================================
import customtkinter as ctk
from utils.ui_utils import get_centered_geometry
from services.friend_service import FriendService
from core.event_bus import EventBus
from core.i18n import translate


class FriendsModal(ctk.CTkToplevel):
    def __init__(self, master, game_state):
        super().__init__(master)
        self.title(translate("social.friends_title"))
        self.attributes('-topmost', True)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.geometry(get_centered_geometry(master, width=400, height=500))
        self.game_state = game_state

        EventBus.subscribe("SOCIAL_FRIENDS_UPDATED", self._on_update)
        EventBus.subscribe("SOCIAL_FRIEND_STATUS", self._on_update)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.setup_ui()
        self.update_list()

    def destroy(self):
        EventBus.unsubscribe("SOCIAL_FRIENDS_UPDATED", self._on_update)
        EventBus.unsubscribe("SOCIAL_FRIEND_STATUS", self._on_update)
        super().destroy()

    def _on_update(self, data=None):
        self.after(0, self.update_list)

    def setup_ui(self):
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(add_frame, text=translate("social.add_friend_section"), font=("Helvetica", 14, "bold")).pack(
            pady=(10, 5))

        self.entry_name = ctk.CTkEntry(add_frame, placeholder_text=translate("social.name_placeholder"), width=150)
        self.entry_name.pack(side="left", padx=(15, 5), pady=(0, 15))

        self.entry_code = ctk.CTkEntry(add_frame, placeholder_text=translate("social.code_placeholder"), width=130)
        self.entry_code.pack(side="left", padx=5, pady=(0, 15))

        self.btn_add = ctk.CTkButton(add_frame, text="+", width=40, fg_color="#1DB954", hover_color="#14833b",
                                     command=self.add_friend)
        self.btn_add.pack(side="left", padx=(5, 15), pady=(0, 15))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

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
            status_text = translate("social.status_online") if is_online else translate("social.status_offline")

            dot = ctk.CTkLabel(row, text="●", text_color=color, font=("Helvetica", 16))
            dot.pack(side="left", padx=(10, 5))

            # Tooltip-ähnlicher Effekt via Hover-Text (optional)
            ctk.CTkLabel(row, text=f_data["name"], font=("Helvetica", 14, "bold")).pack(side="left")

            ctk.CTkButton(row, text="✖", width=30, height=24, fg_color="#c0392b", hover_color="#e74c3c",
                          command=lambda pid=pub_id: FriendService.remove_friend(pid)).pack(side="right", padx=10)

    def add_friend(self):
        name = self.entry_name.get().strip()
        code = self.entry_code.get().strip()
        if name and code:
            success = FriendService.add_friend(name, code)
            if success:
                self.entry_name.delete(0, 'end')
                self.entry_code.delete(0, 'end')