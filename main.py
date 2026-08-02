#!/usr/bin/env python3
import yaml
import logging
import signal
import sys
from typing import Optional, Dict, Any

from sip_client import SIPClient, Call
from mqtt_handler import MQTTHandler
from audio import PulseAudioHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SIPMQTTClient:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.sip_client: Optional[SIPClient] = None
        self.mqtt_handler: Optional[MQTTHandler] = None
        self.audio_handler: Optional[PulseAudioHandler] = None
        self.current_call: Optional[Call] = None
        self.running = False

        self._setup_handlers()

    def _setup_handlers(self) -> None:
        sip_config = self.config["sip"]
        self.sip_client = SIPClient(
            host=sip_config["trunk_host"],
            port=sip_config["trunk_port"],
            username=sip_config["username"],
            password=sip_config["password"],
            display_name=sip_config["display_name"],
            user_agent=sip_config["user_agent"],
        )
        self.sip_client.on_incoming_call = self._on_incoming_call
        self.sip_client.on_call_ended = self._on_call_ended
        self.sip_client.on_dtmf = self._on_dtmf

        mqtt_config = self.config["mqtt"]
        lwt_config = mqtt_config.get("lwt", {})
        self.mqtt_handler = MQTTHandler(
            broker_host=mqtt_config["broker_host"],
            broker_port=mqtt_config["broker_port"],
            username=mqtt_config.get("username", ""),
            password=mqtt_config.get("password", ""),
            client_id=mqtt_config["client_id"],
            will_topic=lwt_config.get("topic", "sip/status"),
            will_message=lwt_config.get("message", "offline"),
            will_qos=lwt_config.get("qos", 1),
            will_retain=lwt_config.get("retain", True),
        )
        self.mqtt_handler.set_topics(mqtt_config["topics"])
        self.mqtt_handler.on_call_control = self._on_call_control
        self.mqtt_handler.on_audio_control = self._on_audio_control

        audio_config = self.config["audio"]
        self.audio_handler = PulseAudioHandler(
            sample_rate=audio_config["sample_rate"],
            channels=audio_config["channels"],
            chunk_size=audio_config["chunk_size"],
            pulse_server=audio_config["pulse_server"],
            sink_name=audio_config["sink_name"],
            source_name=audio_config["source_name"],
        )

    def start(self) -> None:
        logger.info("Starting SIP-MQTT Client")

        self.sip_client.start()
        self.mqtt_handler.start()
        self.audio_handler.start()

        self.running = True
        self.mqtt_handler.publish_call_status("ready")

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        while self.running:
            signal.pause()

    def stop(self) -> None:
        logger.info("Stopping SIP-MQTT Client")
        self.running = False

        if self.current_call and self.current_call.active:
            self.sip_client.hangup_call()

        self.mqtt_handler.set_offline()
        self.sip_client.stop()
        self.mqtt_handler.stop()
        self.audio_handler.stop()

        logger.info("SIP-MQTT Client stopped")

    def _signal_handler(self, signum, frame) -> None:
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)

    def _on_incoming_call(self, call: Call) -> None:
        logger.info(f"Incoming call from {call.caller_id}")
        self.current_call = call
        self.mqtt_handler.publish_call_status(
            "incoming", caller_id=call.caller_id, call_id=call.call_id
        )

    def _on_call_ended(self, reason: str) -> None:
        logger.info(f"Call ended: {reason}")
        self.mqtt_handler.publish_call_status(
            "ended", caller_id=self.current_call.caller_id if self.current_call else "",
            call_id=self.current_call.call_id if self.current_call else ""
        )
        self.current_call = None
        self.audio_handler.stop()

    def _on_dtmf(self, digit: str) -> None:
        logger.info(f"DTMF received: {digit}")
        self.mqtt_handler.publish_dtmf(digit)

    def _on_call_control(self, payload: Dict[str, Any]) -> None:
        action = payload.get("action")
        logger.info(f"Call control action: {action}")

        if action == "answer":
            self._handle_answer()
        elif action == "hangup":
            self._handle_hangup()
        elif action == "reject":
            self._handle_reject()

    def _on_audio_control(self, payload: Dict[str, Any]) -> None:
        action = payload.get("action")
        logger.info(f"Audio control action: {action}")

        if action == "start":
            self.audio_handler.start()
        elif action == "stop":
            self.audio_handler.stop()

    def _handle_answer(self) -> None:
        if self.current_call and not self.current_call.answered:
            logger.info("Answering call")
            self.current_call.answer()
            self.audio_handler.start()
            self.mqtt_handler.publish_call_status(
                "answered", caller_id=self.current_call.caller_id,
                call_id=self.current_call.call_id
            )

    def _handle_hangup(self) -> None:
        if self.current_call:
            logger.info("Hanging up call")
            self.sip_client.hangup_call()
            self.mqtt_handler.publish_call_status(
                "hungup", caller_id=self.current_call.caller_id,
                call_id=self.current_call.call_id
            )

    def _handle_reject(self) -> None:
        if self.current_call:
            logger.info("Rejecting call")
            self.current_call.hangup()
            self.mqtt_handler.publish_call_status(
                "rejected", caller_id=self.current_call.caller_id,
                call_id=self.current_call.call_id
            )
            self.current_call = None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SIP-MQTT Client")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    args = parser.parse_args()

    client = SIPMQTTClient(args.config)

    try:
        client.start()
    except KeyboardInterrupt:
        client.stop()


if __name__ == "__main__":
    main()
