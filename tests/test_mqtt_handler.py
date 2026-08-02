import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from mqtt_handler.handler import MQTTHandler


class TestMQTTHandler:
    @pytest.fixture
    def mqtt_handler(self):
        handler = MQTTHandler(
            broker_host="localhost",
            broker_port=1883,
            username="testuser",
            password="testpass",
            client_id="test-client-001",
        )
        return handler

    @pytest.fixture
    def mock_mqtt_client(self):
        with patch("mqtt_handler.handler.mqtt") as mock:
            mock_client = MagicMock()
            mock.Client.return_value = mock_client
            yield mock_client

    def test_init(self, mqtt_handler):
        assert mqtt_handler.broker_host == "localhost"
        assert mqtt_handler.broker_port == 1883
        assert mqtt_handler.username == "testuser"
        assert mqtt_handler.password == "testpass"
        assert mqtt_handler.client_id == "test-client-001"
        assert mqtt_handler.client is None
        assert mqtt_handler.running is False

    def test_set_topics(self, mqtt_handler):
        topics = {
            "call_status": "sip/call/status",
            "call_control": "sip/call/control",
            "dtmf": "sip/dtmf",
        }
        mqtt_handler.set_topics(topics)
        assert mqtt_handler.topics == topics

    def test_start(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.start()
        assert mqtt_handler.running is True
        assert mqtt_handler.client is not None
        mock_mqtt_client.connect.assert_called_with("localhost", 1883, 60)
        mock_mqtt_client.subscribe.assert_called()

    def test_start_without_auth(self):
        handler = MQTTHandler(
            broker_host="localhost",
            broker_port=1883,
            client_id="test-client-002",
        )
        with patch("mqtt_handler.handler.mqtt") as mock:
            mock_client = MagicMock()
            mock.Client.return_value = mock_client
            handler.start()
            mock_client.username_pw_set.assert_not_called()

    def test_stop(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.start()
        mqtt_handler.stop()
        assert mqtt_handler.running is False
        mock_mqtt_client.disconnect.assert_called()

    def test_on_connect_success(self, mqtt_handler, mock_mqtt_client, caplog):
        mqtt_handler.set_topics({"call_status": "sip/call/status"})
        mqtt_handler._on_connect(mock_mqtt_client, None, None, 0)
        mock_mqtt_client.subscribe.assert_called_with("sip/call/status")
        assert "Connected to MQTT broker" in caplog.text

    def test_on_connect_failure(self, mqtt_handler, mock_mqtt_client, caplog):
        mqtt_handler._on_connect(mock_mqtt_client, None, None, 1)
        assert "Failed to connect" in caplog.text

    def test_on_message_call_control(self, mqtt_handler, mock_mqtt_client):
        callback_called = []
        mqtt_handler.on_call_control = lambda p: callback_called.append(p)
        msg = MagicMock()
        msg.topic = "sip/call/control"
        msg.payload = json.dumps({"action": "answer"}).encode()
        mqtt_handler.set_topics({"call_control": "sip/call/control"})
        mqtt_handler._on_message(mock_mqtt_client, None, msg)
        assert len(callback_called) == 1
        assert callback_called[0]["action"] == "answer"

    def test_on_message_audio_control(self, mqtt_handler, mock_mqtt_client):
        callback_called = []
        mqtt_handler.on_audio_control = lambda p: callback_called.append(p)
        msg = MagicMock()
        msg.topic = "sip/audio/control"
        msg.payload = json.dumps({"action": "start"}).encode()
        mqtt_handler.set_topics({"audio_control": "sip/audio/control"})
        mqtt_handler._on_message(mock_mqtt_client, None, msg)
        assert len(callback_called) == 1
        assert callback_called[0]["action"] == "start"

    def test_on_message_invalid_json(self, mqtt_handler, mock_mqtt_client):
        msg = MagicMock()
        msg.topic = "sip/call/control"
        msg.payload = b"invalid json"
        mqtt_handler.set_topics({"call_control": "sip/call/control"})
        mqtt_handler._on_message(mock_mqtt_client, None, msg)

    def test_on_message_unknown_topic(self, mqtt_handler, mock_mqtt_client):
        msg = MagicMock()
        msg.topic = "unknown/topic"
        msg.payload = json.dumps({}).encode()
        mqtt_handler._on_message(mock_mqtt_client, None, msg)

    def test_on_disconnect(self, mqtt_handler, mock_mqtt_client, caplog):
        mqtt_handler.running = True
        with patch.object(mock_mqtt_client, "reconnect"):
            mqtt_handler._on_disconnect(mock_mqtt_client, None, 0)
            assert "Disconnected from MQTT broker" in caplog.text

    def test_on_disconnect_not_running(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.running = False
        mqtt_handler._on_disconnect(mock_mqtt_client, None, 0)

    def test_on_disconnect_reconnect_failure(self, mqtt_handler, mock_mqtt_client, caplog):
        mqtt_handler.running = True
        mock_mqtt_client.reconnect.side_effect = Exception("Connection failed")
        mqtt_handler._on_disconnect(mock_mqtt_client, None, 0)
        assert "Reconnection failed" in caplog.text

    def test_publish(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = True
        mqtt_handler.publish("test/topic", {"key": "value"})
        mock_mqtt_client.publish.assert_called_with("test/topic", json.dumps({"key": "value"}))

    def test_publish_not_connected(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = False
        mqtt_handler.publish("test/topic", {"key": "value"})
        mock_mqtt_client.publish.assert_not_called()

    def test_publish_no_client(self, mqtt_handler):
        mqtt_handler.client = None
        mqtt_handler.publish("test/topic", {"key": "value"})

    def test_publish_call_status(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = True
        mqtt_handler.set_topics({"call_status": "sip/call/status"})
        mqtt_handler.publish_call_status("incoming", "123456", "call-123")
        mock_mqtt_client.publish.assert_called()
        call_args = mock_mqtt_client.publish.call_args
        assert call_args[0][0] == "sip/call/status"
        payload = json.loads(call_args[0][1])
        assert payload["status"] == "incoming"
        assert payload["caller_id"] == "123456"
        assert "timestamp" in payload

    def test_publish_dtmf(self, mqtt_handler, mock_mqtt_client):
        mqtt_handler.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = True
        mqtt_handler.set_topics({"dtmf": "sip/dtmf"})
        mqtt_handler.publish_dtmf("5", 100)
        mock_mqtt_client.publish.assert_called()
        call_args = mock_mqtt_client.publish.call_args
        assert call_args[0][0] == "sip/dtmf"
        payload = json.loads(call_args[0][1])
        assert payload["digit"] == "5"
        assert payload["duration"] == 100
        assert "timestamp" in payload

    def test_get_timestamp(self, mqtt_handler):
        timestamp = mqtt_handler._get_timestamp()
        assert isinstance(timestamp, float)
        assert timestamp > 0
