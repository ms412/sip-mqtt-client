import pytest
import yaml
from unittest.mock import Mock, patch, MagicMock
from main import SIPMQTTClient, main


class TestSIPMQTTClient:
    @pytest.fixture
    def mock_config(self):
        return {
            "sip": {
                "trunk_host": "sip.example.com",
                "trunk_port": 5060,
                "username": "testuser",
                "password": "testpass",
                "display_name": "Test Client",
                "user_agent": "Test/1.0",
                "register": True,
                "register_expiry": 3600,
            },
            "mqtt": {
                "broker_host": "localhost",
                "broker_port": 1883,
                "username": "",
                "password": "",
                "client_id": "test-client-001",
                "topics": {
                    "incoming_call": "sip/call/incoming",
                    "call_status": "sip/call/status",
                    "call_control": "sip/call/control",
                    "dtmf": "sip/dtmf",
                    "audio_control": "sip/audio/control",
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
            "logging": {
                "level": "INFO",
                "file": "test.log",
            },
        }

    @pytest.fixture
    def sip_mqtt_client(self, mock_config):
        with patch("main.open", MagicMock()):
            with patch("main.yaml.safe_load", return_value=mock_config):
                with patch("main.SIPClient"):
                    with patch("main.MQTTHandler"):
                        with patch("main.PulseAudioHandler"):
                            client = SIPMQTTClient("config.yaml")
                            return client

    def test_init(self, sip_mqtt_client, mock_config):
        assert sip_mqtt_client.config == mock_config
        assert sip_mqtt_client.sip_client is not None
        assert sip_mqtt_client.mqtt_handler is not None
        assert sip_mqtt_client.audio_handler is not None
        assert sip_mqtt_client.current_call is None
        assert sip_mqtt_client.running is False

    def test_setup_handlers(self, mock_config):
        with patch("main.SIPClient") as mock_sip:
            with patch("main.MQTTHandler") as mock_mqtt:
                with patch("main.PulseAudioHandler") as mock_audio:
                    with patch("main.open", MagicMock()):
                        with patch("main.yaml.safe_load", return_value=mock_config):
                            client = SIPMQTTClient("config.yaml")
                            mock_sip.assert_called_once()
                            mock_mqtt.assert_called_once()
                            mock_audio.assert_called_once()

    def test_start(self, sip_mqtt_client):
        with patch("main.signal"):
            with patch.object(sip_mqtt_client.sip_client, "start"):
                with patch.object(sip_mqtt_client.mqtt_handler, "start"):
                    with patch.object(sip_mqtt_client.audio_handler, "start"):
                        with patch.object(sip_mqtt_client.mqtt_handler, "publish_call_status"):
                            sip_mqtt_client.running = True
                            with patch("main.signal.pause"):
                                sip_mqtt_client.start()
                            assert sip_mqtt_client.running is False

    def test_stop(self, sip_mqtt_client):
        mock_call = MagicMock()
        mock_call.active = True
        sip_mqtt_client.current_call = mock_call
        with patch.object(sip_mqtt_client.sip_client, "hangup_call"):
            with patch.object(sip_mqtt_client.sip_client, "stop"):
                with patch.object(sip_mqtt_client.mqtt_handler, "stop"):
                    with patch.object(sip_mqtt_client.audio_handler, "stop"):
                        sip_mqtt_client.stop()
                        assert sip_mqtt_client.running is False

    def test_stop_no_call(self, sip_mqtt_client):
        sip_mqtt_client.current_call = None
        with patch.object(sip_mqtt_client.sip_client, "stop"):
            with patch.object(sip_mqtt_client.mqtt_handler, "stop"):
                with patch.object(sip_mqtt_client.audio_handler, "stop"):
                    sip_mqtt_client.stop()

    def test_signal_handler(self, sip_mqtt_client, capsys):
        with patch.object(sip_mqtt_client, "stop"):
            with pytest.raises(SystemExit):
                sip_mqtt_client._signal_handler(2, None)

    def test_on_incoming_call(self, sip_mqtt_client):
        mock_call = MagicMock()
        mock_call.caller_id = "123456"
        mock_call.call_id = "call-123"
        with patch.object(sip_mqtt_client.mqtt_handler, "publish_call_status") as mock_publish:
            sip_mqtt_client._on_incoming_call(mock_call)
            assert sip_mqtt_client.current_call == mock_call
            mock_publish.assert_called_with("incoming", caller_id="123456", call_id="call-123")

    def test_on_call_ended(self, sip_mqtt_client):
        mock_call = MagicMock()
        mock_call.caller_id = "123456"
        mock_call.call_id = "call-123"
        sip_mqtt_client.current_call = mock_call
        with patch.object(sip_mqtt_client.mqtt_handler, "publish_call_status") as mock_publish:
            with patch.object(sip_mqtt_client.audio_handler, "stop"):
                sip_mqtt_client._on_call_ended("remote_hangup")
                mock_publish.assert_called_with(
                    "ended", caller_id="123456", call_id="call-123"
                )
                assert sip_mqtt_client.current_call is None

    def test_on_call_ended_no_call(self, sip_mqtt_client):
        sip_mqtt_client.current_call = None
        with patch.object(sip_mqtt_client.mqtt_handler, "publish_call_status"):
            with patch.object(sip_mqtt_client.audio_handler, "stop"):
                sip_mqtt_client._on_call_ended("remote_hangup")

    def test_on_dtmf(self, sip_mqtt_client):
        with patch.object(sip_mqtt_client.mqtt_handler, "publish_dtmf") as mock_publish:
            sip_mqtt_client._on_dtmf("5")
            mock_publish.assert_called_with("5")

    def test_on_call_control_answer(self, sip_mqtt_client):
        with patch.object(sip_mqtt_client, "_handle_answer") as mock_answer:
            sip_mqtt_client._on_call_control({"action": "answer"})
            mock_answer.assert_called()

    def test_on_call_control_hangup(self, sip_mqtt_client):
        with patch.object(sip_mqtt_client, "_handle_hangup") as mock_hangup:
            sip_mqtt_client._on_call_control({"action": "hangup"})
            mock_hangup.assert_called()

    def test_on_call_control_reject(self, sip_mqtt_client):
        with patch.object(sip_mqtt_client, "_handle_reject") as mock_reject:
            sip_mqtt_client._on_call_control({"action": "reject"})
            mock_reject.assert_called()

    def test_on_audio_control_start(self, sip_mqtt_client):
        with patch.object(sip_mqtt_client.audio_handler, "start") as mock_start:
            sip_mqtt_client._on_audio_control({"action": "start"})
            mock_start.assert_called()

    def test_on_audio_control_stop(self, sip_mqtt_client):
        with patch.object(sip_mqtt_client.audio_handler, "stop") as mock_stop:
            sip_mqtt_client._on_audio_control({"action": "stop"})
            mock_stop.assert_called()

    def test_handle_answer(self, sip_mqtt_client):
        mock_call = MagicMock()
        mock_call.answered = False
        sip_mqtt_client.current_call = mock_call
        with patch.object(mock_call, "answer"):
            with patch.object(sip_mqtt_client.audio_handler, "start"):
                with patch.object(sip_mqtt_client.mqtt_handler, "publish_call_status"):
                    sip_mqtt_client._handle_answer()
                    mock_call.answer.assert_called()

    def test_handle_answer_no_call(self, sip_mqtt_client):
        sip_mqtt_client.current_call = None
        sip_mqtt_client._handle_answer()

    def test_handle_answer_already_answered(self, sip_mqtt_client):
        mock_call = MagicMock()
        mock_call.answered = True
        sip_mqtt_client.current_call = mock_call
        sip_mqtt_client._handle_answer()

    def test_handle_hangup(self, sip_mqtt_client):
        mock_call = MagicMock()
        mock_call.caller_id = "123456"
        mock_call.call_id = "call-123"
        sip_mqtt_client.current_call = mock_call
        with patch.object(sip_mqtt_client.sip_client, "hangup_call"):
            with patch.object(sip_mqtt_client.mqtt_handler, "publish_call_status") as mock_publish:
                sip_mqtt_client._handle_hangup()
                mock_publish.assert_called_with("hungup", caller_id="123456", call_id="call-123")

    def test_handle_hangup_no_call(self, sip_mqtt_client):
        sip_mqtt_client.current_call = None
        sip_mqtt_client._handle_hangup()

    def test_handle_reject(self, sip_mqtt_client):
        mock_call = MagicMock()
        mock_call.caller_id = "123456"
        mock_call.call_id = "call-123"
        sip_mqtt_client.current_call = mock_call
        with patch.object(mock_call, "hangup"):
            with patch.object(sip_mqtt_client.mqtt_handler, "publish_call_status") as mock_publish:
                sip_mqtt_client._handle_reject()
                mock_call.hangup.assert_called()
                mock_publish.assert_called_with("rejected", caller_id="123456", call_id="call-123")
                assert sip_mqtt_client.current_call is None

    def test_handle_reject_no_call(self, sip_mqtt_client):
        sip_mqtt_client.current_call = None
        sip_mqtt_client._handle_reject()


class TestMain:
    def test_main(self):
        with patch("main.SIPMQTTClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            mock_instance.start.side_effect = KeyboardInterrupt()
            with patch("sys.argv", ["main.py"]):
                main()
                mock_instance.stop.assert_called()

    def test_main_with_config(self):
        with patch("main.SIPMQTTClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            mock_instance.start.side_effect = KeyboardInterrupt()
            with patch("sys.argv", ["main.py", "-c", "custom.yaml"]):
                main()
                mock_client.assert_called_with("custom.yaml")

    def test_main_keyboard_interrupt(self):
        with patch("main.SIPMQTTClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            mock_instance.start.side_effect = KeyboardInterrupt()
            with patch("sys.argv", ["main.py"]):
                main()
                mock_instance.stop.assert_called()


class TestConfigLoading:
    def test_config_file_not_found(self):
        with patch("main.open", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                SIPMQTTClient("nonexistent.yaml")

    def test_config_invalid_yaml(self):
        with patch("main.open", MagicMock()):
            with patch("main.yaml.safe_load", side_effect=yaml.YAMLError()):
                with pytest.raises(yaml.YAMLError):
                    SIPMQTTClient("config.yaml")
