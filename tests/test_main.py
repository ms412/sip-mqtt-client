import pytest
from unittest.mock import Mock, patch, MagicMock
from main import SIPMQTTClient


class TestSIPMQTTClient:
    @pytest.fixture
    def mock_config(self):
        return {
            "sip": {
                "trunk_host": "sip.example.com",
                "trunk_port": 5060,
                "username": "testuser",
                "password": "testpass",
                "display_name": "Test",
                "user_agent": "Test/1.0",
            },
            "mqtt": {
                "broker_host": "localhost",
                "broker_port": 1883,
                "client_id": "test-client",
                "topics": {
                    "call_status": "sip/call/status",
                    "call_control": "sip/call/control",
                },
            },
            "audio": {
                "sample_rate": 8000,
                "channels": 1,
                "chunk_size": 160,
                "pulse_server": "localhost",
                "sink_name": "sip_output",
                "source_name": "sip_input",
            },
        }

    @pytest.fixture
    def sip_mqtt_client(self, mock_config):
        with patch("main.open", MagicMock()):
            with patch("main.yaml.safe_load", return_value=mock_config):
                with patch("main.SIPClient"):
                    with patch("main.MQTTHandler"):
                        with patch("main.PulseAudioHandler"):
                            return SIPMQTTClient("config.yaml")

    def test_init(self, sip_mqtt_client):
        assert sip_mqtt_client.sip_client is not None
        assert sip_mqtt_client.mqtt_handler is not None
