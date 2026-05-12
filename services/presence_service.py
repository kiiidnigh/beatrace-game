# ================================================
# FILE: services/presence_service.py
# ================================================
import json
import logging
import threading
import paho.mqtt.client as mqtt
from config import settings
from core.event_bus import EventBus
from services.identity_service import IdentityService
from services.friend_service import FriendService


class PresenceService:
    def __init__(self):
        self.public_id = IdentityService.get_public_id()
        self.status_topic = f"beatrace/status/{self.public_id}"
        self.invite_topic = f"beatrace/invites/{self.public_id}"

        self.client = mqtt.Client(client_id=f"presence_{self.public_id}", clean_session=True)

        # WICHTIG: Das Testament (Last Will). Wenn die App abstürzt, meldet der Server uns als offline!
        lwt_payload = json.dumps({"status": "offline", "user": self.public_id})
        self.client.will_set(self.status_topic, lwt_payload, qos=1, retain=True)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        EventBus.subscribe("SOCIAL_FRIENDS_UPDATED", lambda d: self._refresh_subscriptions())

    def start(self):
        logging.info("[PresenceService] Starte dezentrales Social Network...")
        threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self):
        try:
            self.client.connect(settings.BROKER, settings.PORT, 60)
            self.client.loop_start()
        except Exception as e:
            logging.error(f"[PresenceService] Verbindungsfehler: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        logging.info("[PresenceService] Verbunden! Sende Online-Status.")

        # retain=True sorgt dafür, dass Freunde, die NACH uns online kommen, den Status sofort erhalten
        online_payload = json.dumps({"status": "online", "user": self.public_id})
        self.client.publish(self.status_topic, online_payload, qos=1, retain=True)

        self._refresh_subscriptions()

    def _refresh_subscriptions(self):
        self.client.subscribe(self.invite_topic)
        friends = FriendService.get_friends()
        for f_id in friends.keys():
            self.client.subscribe(f"beatrace/status/{f_id}")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload_str = msg.payload.decode("utf-8")
            data = json.loads(payload_str)

            # 1. Status Update eines Freundes
            if topic.startswith("beatrace/status/"):
                f_id = topic.split("/")[-1]
                if f_id != self.public_id:
                    EventBus.emit("SOCIAL_FRIEND_STATUS", data={"public_id": f_id, "status": data.get("status")})

            # 2. Einladung erhalten
            elif topic == self.invite_topic:
                self._handle_invite(data)

        except Exception as e:
            pass

    def _handle_invite(self, data):
        sender_id = data.get("sender_id")
        token = data.get("token")
        friends = FriendService.get_friends()

        # ZERO-TRUST REGEL: Nur Freunde mit korrektem kryptografischem Token werden durchgelassen!
        if sender_id in friends and friends[sender_id].get("token") == token:
            sender_name = friends[sender_id].get("name", "Ein Freund")
            data["sender_name"] = sender_name
            EventBus.emit("SOCIAL_INVITE_RECEIVED", data=data)
        else:
            logging.warning(f"[PresenceService] Blockierte Spam-Einladung von {sender_id}")

    def stop(self):
        offline_payload = json.dumps({"status": "offline", "user": self.public_id})
        self.client.publish(self.status_topic, offline_payload, qos=1, retain=True)
        self.client.loop_stop()
        self.client.disconnect()