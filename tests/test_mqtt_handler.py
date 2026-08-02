import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from mqtt_handler.handler import MQTTHandler


class TestMQTTHandler:
    @pytest.fixture
    def mqtt_handler(self):
        return MQTTHandler(
            broker_host="localhost",
            broker_port=1883,
            client_id="test-client-001",
        )

    @pytest.fixture
    def mock_mqtt_client(self):
        with patch("mqtt_handler.handler.mqtt") as mock:
            mock_client = MagicMock()
            mock.Client.return_value = mock_client
            yield mock_client

    def test_init(self, mqtt_handler):
        assert mqtt_handler.broker_host == "localhost"
        assert mqtt_handler.client_id == "test-client-001"

    def test_start(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.start()
        assert mqtt_handler.running is True
        mock_mqtt_client.connect.assert_called()

    def test_set_online(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = True
        mqtt_handler.set_online()
        mock_mqtt_client.publish.assert_called()
