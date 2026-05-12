# ================================================
# FILE: services/presence_service.py
# ================================================
import json
import logging
import paho.mqtt.client as mqtt
from services.identity_service import IdentityService
from services.friend_service import FriendService
from core.event_bus import EventBus


class PresenceService:
    def __init__(self):
        self.client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.my_pub_id = IdentityService.get_public_id()

        # --- NEU: Das Testament (Last Will and Testament) ---
        # Wenn wir unsauber die Verbindung verlieren, funkt der Broker automatisch das hier:
        lwt_payload = json.dumps({"status": "offline"})
        self.client.will_set(f"beatrace/presence/status/{self.my_pub_id}", lwt_payload, qos=1, retain=True)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        self.is_running = False

        # Reagiere sofort, wenn sich die Freundesliste ändert
        EventBus.subscribe("SOCIAL_FRIENDS_UPDATED",
                           lambda d: self._update_subscriptions() if self.is_running else None)

    def start(self):
        if self.is_running: return
        logging.info("[PresenceService] Starte LWT Social Network...")
        self.is_running = True

        broker_address = "broker.hivemq.com"
        broker_port = 1883

        try:
            # keepalive=60: Der Broker prüft jede Minute, ob wir noch da sind.
            # Wenn nicht, feuert das Testament!
            self.client.connect(broker_address, broker_port, keepalive=60)

            # loop_start managt den Netzwerk-Thread automatisch im Hintergrund! Keine while-Schleife mehr nötig.
            self.client.loop_start()
        except Exception as e:
            logging.error(f"[PresenceService] Fehler: {e}")

    def _update_subscriptions(self):
        """Abonniert die Status-Kanäle aller Freunde und funkt das eigene Update"""
        self._broadcast_presence()

        friends = FriendService.get_friends()
        for f_id in friends.keys():
            # Wir lauschen spezifisch auf die Status-Kanäle unserer Freunde
            self.client.subscribe(f"beatrace/presence/status/{f_id}", qos=1)

    def _broadcast_presence(self):
        """Funkt den eigenen Status mit retain=True, damit Nachzügler ihn sofort sehen"""
        my_name = IdentityService.get_display_name()
        payload = json.dumps({
            "status": "online",
            "name": my_name
        })

        # retain=True: Der Server pinnt die Nachricht an.
        # Jeder der in Zukunft abonniert, kriegt sie SOFORT.
        self.client.publish(f"beatrace/presence/status/{self.my_pub_id}", payload, qos=1, retain=True)

    def _on_connect(self, client, userdata, flags, rc):
        logging.info("[PresenceService] Verbunden! Richte Briefkasten & Status-Kanäle ein...")

        # 1. Unseren eigenen Briefkasten abonnieren
        client.subscribe(f"beatrace/social/{self.my_pub_id}/inbox", qos=1)

        # 2. Die Kanäle der Freunde abonnieren
        self._update_subscriptions()

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())

            # --- STATUS & NAMENS-UPDATE ---
            if topic.startswith("beatrace/presence/status/"):
                sender_pub_id = topic.split("/")[-1]

                # Wir ignorieren unsere eigenen Echo-Nachrichten
                if sender_pub_id == self.my_pub_id:
                    return

                status = payload.get("status")
                sender_name = payload.get("name")

                EventBus.emit("SOCIAL_FRIEND_STATUS", {"public_id": sender_pub_id, "status": status})

                if sender_name:
                    FriendService.update_friend_name(sender_pub_id, sender_name)

            # --- BRIEFKASTEN (Anfragen, Löschungen & Einladungen) ---
            elif topic == f"beatrace/social/{self.my_pub_id}/inbox":
                msg_type = payload.get("type")

                if msg_type == "friend_request":
                    EventBus.emit("SOCIAL_FRIEND_REQUEST_RECEIVED", payload)

                elif msg_type == "friend_accept":
                    friend_name = payload.get("sender_name")
                    friend_identity = payload.get("sender_identity")
                    FriendService.add_friend(friend_name, friend_identity)

                elif msg_type == "friend_remove":
                    friend_identity = payload.get("sender_identity")
                    if friend_identity:
                        target_pub_id = friend_identity.split("#")[0]
                        FriendService.remove_friend(target_pub_id)

                elif msg_type == "lobby_invite":
                    EventBus.emit("SOCIAL_INVITE_RECEIVED", payload)

        except Exception as e:
            logging.error(f"[PresenceService] Parsing Fehler: {e}")

    def stop(self):
        self.is_running = False
        if self.client:
            # Absichtliches Offline-Gehen (überschreibt die Retained Message)
            payload = json.dumps({"status": "offline"})
            self.client.publish(f"beatrace/presence/status/{self.my_pub_id}", payload, qos=1, retain=True)

            self.client.loop_stop()
            self.client.disconnect()