import paho.mqtt.client as mqtt
import json
import uuid
import logging
from config import settings
from core.event_bus import EventBus


class NetworkManager:
    def __init__(self):
        self.my_name = ""
        self.room_code = ""
        self.is_connected = False
        self.client_id = str(uuid.uuid4())

        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def connect(self, my_name, room_code):
        self.my_name = my_name
        self.room_code = room_code.upper()
        self.topic = f"{settings.ROOM_SECRET}/{self.room_code}"

        if not self.is_connected:
            try:
                logging.info(f"[Network] Verbinde mit Broker: {settings.BROKER}:{settings.PORT}...")
                self.client.connect(settings.BROKER, settings.PORT, 60)
                self.client.loop_start()
                self.is_connected = True
            except Exception as e:
                logging.error(f"[Network] Konnte nicht mit dem Netzwerk verbinden: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        logging.info(f"[Network] [{self.my_name}] Erfolgreich verbunden! Betrete Raum: {self.room_code}")
        self.client.subscribe(self.topic)
        EventBus.emit("NET_CONNECTED")

    def _on_message(self, client, userdata, msg):
        payload_str = msg.payload.decode("utf-8")
        try:
            payload = json.loads(payload_str)
            sender_id = payload.get("client_id")
            command = payload.get("command")

            # Eigene Nachrichten ignorieren wir
            if sender_id != self.client_id:
                logging.debug(f"[Network] Nachricht empfangen: {command} von {payload.get('sender')}")
                EventBus.emit(f"NET_{command}", data=payload)
        except json.JSONDecodeError as e:
            logging.warning(f"[Network] Konnte Payload nicht decodieren: {e}")

    def send_signal(self, command, data=None):
        if self.is_connected:
            payload = {
                "sender": self.my_name,
                "client_id": self.client_id,
                "command": command,
                "data": data if data else {}
            }
            message = json.dumps(payload)
            self.client.publish(self.topic, message)
            logging.debug(f"[Network] Signal gesendet: {command}")

    def disconnect(self):
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logging.info("[Network] Verbindung getrennt.")