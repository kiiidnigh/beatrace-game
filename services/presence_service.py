# ================================================
# FILE: services/presence_service.py
# ================================================
import json
import logging
import paho.mqtt.client as mqtt
from core.event_bus import EventBus
from services.base_service import BaseService


class PresenceService(BaseService):
    def __init__(self, identity_service, friend_service):
        super().__init__()
        self.identity_service = identity_service
        self.friend_service = friend_service

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
        self.my_pub_id = self.identity_service.get_public_id()

        lwt_payload = json.dumps({"status": "offline"})
        self.client.will_set(f"beatrace/presence/status/{self.my_pub_id}", lwt_payload, qos=1, retain=True)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.is_running = False

        self._listeners = {
            "SOCIAL_FRIENDS_UPDATED": lambda d: self._update_subscriptions() if self.is_running else None,
            "CMD_SEND_SOCIAL_MESSAGE": self._handle_send_message,
            "CMD_BROADCAST_PRESENCE": lambda d: self._broadcast_presence() if self.is_running else None
        }
        self.register_listeners()

    def start(self):
        if self.is_running: return
        logging.info("[PresenceService] Starte LWT Social Network...")
        self.is_running = True

        broker_address = "broker.hivemq.com"
        broker_port = 1883

        try:
            self.client.connect(broker_address, broker_port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logging.error(f"[PresenceService] Fehler: {e}")

    def _update_subscriptions(self):
        self._broadcast_presence()
        friends = self.friend_service.get_friends()
        for f_id in friends.keys():
            self.client.subscribe(f"beatrace/presence/status/{f_id}", qos=1)

    def _broadcast_presence(self):
        my_name = self.identity_service.get_display_name()
        payload = json.dumps({
            "status": "online",
            "name": my_name
        })
        self.client.publish(f"beatrace/presence/status/{self.my_pub_id}", payload, qos=1, retain=True)

    def _handle_send_message(self, data):
        topic = data.get("topic")
        payload = data.get("payload")

        if topic and payload and self.client and self.is_running:
            self.client.publish(topic, payload, qos=1)
            logging.debug(f"[PresenceService] Social-Nachricht an {topic} gesendet.")
        else:
            logging.warning("[PresenceService] Konnte Nachricht nicht senden (Fehlende Daten oder Offline).")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        logging.info("[PresenceService] Verbunden! Richte Briefkasten & Status-Kanäle ein...")
        client.subscribe(f"beatrace/social/{self.my_pub_id}/inbox", qos=1)
        self._update_subscriptions()

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())

            if topic.startswith("beatrace/presence/status/"):
                sender_pub_id = topic.split("/")[-1]
                if sender_pub_id == self.my_pub_id:
                    return

                status = payload.get("status")
                sender_name = payload.get("name")
                EventBus.emit("SOCIAL_FRIEND_STATUS", {"public_id": sender_pub_id, "status": status})

                if sender_name:
                    self.friend_service.update_friend_name(sender_pub_id, sender_name)

            elif topic == f"beatrace/social/{self.my_pub_id}/inbox":
                msg_type = payload.get("type")

                if msg_type == "friend_request":
                    EventBus.emit("SOCIAL_FRIEND_REQUEST_RECEIVED", payload)
                elif msg_type == "friend_accept":
                    self.friend_service.add_friend(payload.get("sender_name"), payload.get("sender_identity"))
                elif msg_type == "friend_remove":
                    target_pub_id = payload.get("sender_identity").split("#")[0]
                    self.friend_service.remove_friend(target_pub_id)
                elif msg_type == "lobby_invite":
                    EventBus.emit("SOCIAL_INVITE_RECEIVED", payload)
        except Exception as e:
            logging.error(f"[PresenceService] Parsing Fehler: {e}")

    def stop(self):
        self.is_running = False
        if self.client:
            payload = json.dumps({"status": "offline"})
            self.client.publish(f"beatrace/presence/status/{self.my_pub_id}", payload, qos=1, retain=True)
            self.client.loop_stop()
            self.client.disconnect()
        self.cleanup()