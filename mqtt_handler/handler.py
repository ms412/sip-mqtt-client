import json
import logging
import threading
from typing import Optional, Callable, Dict, Any
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTHandler:
    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        username: str = "",
        password: str = "",
        client_id: str = "sip-client-001",
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client: Optional[mqtt.Client] = None
        self.topics: Dict[str, str] = {}
        self.running = False
        self._thread: Optional[threading.Thread] = None

        self.on_incoming_call: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_call_control: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_audio_control: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_topics(self, topics: Dict[str, str]) -> None:
        self.topics = topics

    def start(self) -> None:
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        self.running = True
        self.client.connect(self.broker_host, self.broker_port, 60)
        self._thread = threading.Thread(target=self.client.loop_forever, daemon=True)
        self._thread.start()
        logger.info(f"MQTT client started, connected to {self.broker_host}:{self.broker_port}")

    def stop(self) -> None:
        self.running = False
        if self.client:
            self.client.disconnect()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("MQTT client stopped")

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            logger.info("Connected to MQTT broker")
            for topic in self.topics.values():
                client.subscribe(topic)
                logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker, result code: {rc}")

    def _on_message(self, client, userdata, msg) -> None:
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            payload = msg.payload.decode()

        logger.debug(f"Received message on {topic}: {payload}")

        if topic == self.topics.get("incoming_call"):
            pass
        elif topic == self.topics.get("call_control"):
            if self.on_call_control:
                self.on_call_control(payload)
        elif topic == self.topics.get("audio_control"):
            if self.on_audio_control:
                self.on_audio_control(payload)

    def _on_disconnect(self, client, userdata, rc) -> None:
        logger.info("Disconnected from MQTT broker")
        if self.running:
            logger.info("Attempting to reconnect...")
            try:
                client.reconnect()
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        if self.client and self.client.is_connected():
            self.client.publish(topic, json.dumps(message))
            logger.debug(f"Published to {topic}: {message}")

    def publish_call_status(self, status: str, caller_id: str = "", call_id: str = "") -> None:
        message = {
            "status": status,
            "caller_id": caller_id,
            "call_id": call_id,
            "timestamp": self._get_timestamp(),
        }
        self.publish(self.topics.get("call_status", "sip/call/status"), message)

    def publish_dtmf(self, digit: str, duration: int = 0) -> None:
        message = {
            "digit": digit,
            "duration": duration,
            "timestamp": self._get_timestamp(),
        }
        self.publish(self.topics.get("dtmf", "sip/dtmf"), message)

    def _get_timestamp(self) -> float:
        import time
        return time.time()
