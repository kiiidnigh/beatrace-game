# ================================================
# FILE: ui/components/friends_modal.py
# ================================================
import json
import customtkinter as ctk
from services.friend_service import FriendService
from services.identity_service import IdentityService
from utils.ui_utils import get_centered_geometry
from core.event_bus import EventBus


class FriendsModal(ctk.CTkToplevel):
    def __init__(self, master, game_state=None):
        super().__init__(master)
        self.title("Deine Freunde")
        self.geometry(get_centered_geometry(master, width=500, height=600))
        self.attributes('-topmost', True)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.master_window = master
        self.game_state = game_state

        self.my_id = IdentityService.get_or_create_id()

        # --- Eigener Freundescode Bereich ---
        top_frame = ctk.CTkFrame(self, fg_color="#1e1e1e")
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Dein Freundescode:", font=("Helvetica", 12, "bold"), text_color="gray").pack(
            pady=(10, 5))

        id_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        id_frame.pack(pady=(0, 10))

        id_entry = ctk.CTkEntry(id_frame, font=("Helvetica", 16, "bold"), justify="center", fg_color="transparent",
                                border_width=0, width=150)
        id_entry.insert(0, self.my_id)
        id_entry.configure(state="readonly")
        id_entry.pack(side="left", padx=(0, 10))

        # NEU: Der Copy-Button
        self.copy_btn = ctk.CTkButton(id_frame, text="📋 Kopieren", width=100, fg_color="#333333",
                                      hover_color="#555555", command=self._copy_to_clipboard)
        self.copy_btn.pack(side="left")

        # --- Freund hinzufügen Bereich ---
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.add_entry = ctk.CTkEntry(add_frame, placeholder_text="Freundescode eingeben (z.B. ABCD#123)", width=300)
        self.add_entry.pack(side="left", padx=(0, 10))

        self.add_btn = ctk.CTkButton(add_frame, text="Anfrage senden", width=120, fg_color="#1DB954",
                                     hover_color="#14833b", command=self._send_friend_request)
        self.add_btn.pack(side="left")

        # --- Freundesliste ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Live-Updates abonnieren
        self._update_callback = lambda d=None: self.after(0, self._populate_list)
        EventBus.subscribe("SOCIAL_FRIENDS_UPDATED", self._update_callback)
        EventBus.subscribe("SOCIAL_FRIEND_STATUS", self._update_callback)

        self._populate_list()

    def destroy(self):
        # Event-Listener sauber abmelden!
        EventBus.unsubscribe("SOCIAL_FRIENDS_UPDATED", self._update_callback)
        EventBus.unsubscribe("SOCIAL_FRIEND_STATUS", self._update_callback)
        super().destroy()

    def _copy_to_clipboard(self):
        """Kopiert die ID in die Zwischenablage und gibt visuelles Feedback."""
        self.clipboard_clear()
        self.clipboard_append(self.my_id)

        self.copy_btn.configure(text="✅ Kopiert!", fg_color="#1DB954")
        self.after(2000, lambda: self.copy_btn.configure(text="📋 Kopieren", fg_color="#333333"))

    def _send_friend_request(self):
        target_identity = self.add_entry.get().strip()
        if "#" not in target_identity:
            self.add_btn.configure(text="Ungültig!", fg_color="#c0392b")
            self.after(2000, lambda: self.add_btn.configure(text="Anfrage senden", fg_color="#1DB954"))
            return

        target_pub_id = target_identity.split("#")[0]
        my_identity = IdentityService.get_or_create_id()
        my_name = IdentityService.get_display_name()

        payload = json.dumps({
            "type": "friend_request",
            "sender_name": my_name,
            "sender_identity": my_identity
        })

        topic = f"beatrace/social/{target_pub_id}/inbox"
        if hasattr(self.master_window, 'presence_service'):
            self.master_window.presence_service.client.publish(topic, payload, qos=1)

        self.add_entry.delete(0, 'end')
        self.add_btn.configure(text="Gesendet!", fg_color="#1DB954", state="disabled")
        self.after(2000, lambda: self.add_btn.configure(text="Anfrage senden", state="normal"))

    def _populate_list(self):
        if not hasattr(self, 'scroll_frame') or not self.scroll_frame.winfo_exists():
            return

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        friends = FriendService.get_friends()
        if not friends:
            ctk.CTkLabel(self.scroll_frame, text="Du hast noch keine Freunde hinzugefügt.", text_color="gray").pack(
                pady=20)
            return

        game_state = self.game_state

        for pub_id, data in friends.items():
            f_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#2a2a2a")
            f_frame.pack(fill="x", pady=5)

            name = data.get("name", "Unbekannt")
            is_online = pub_id in game_state.online_friends if game_state else False

            color = "#1DB954" if is_online else "gray"
            status = "Online" if is_online else "Offline"

            ctk.CTkLabel(f_frame, text=name, font=("Helvetica", 14, "bold")).pack(side="left", padx=10, pady=10)
            ctk.CTkLabel(f_frame, text=status, text_color=color).pack(side="left", padx=10)

            ctk.CTkButton(f_frame, text="❌", width=30, fg_color="transparent", hover_color="#c0392b",
                          command=lambda pid=pub_id: self._remove_friend(pid)).pack(side="right", padx=10)

    def _remove_friend(self, pub_id):
        FriendService.remove_friend(pub_id)

        my_identity = IdentityService.get_or_create_id()
        payload = json.dumps({
            "type": "friend_remove",
            "sender_identity": my_identity
        })
        topic = f"beatrace/social/{pub_id}/inbox"

        if hasattr(self.master_window, 'presence_service'):
            self.master_window.presence_service.client.publish(topic, payload, qos=1)

        self._populate_list()