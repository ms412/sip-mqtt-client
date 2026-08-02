import pytest
import socket
import threading
from unittest.mock import Mock, patch, MagicMock
from sip_client.client import SIPClient
from sip_client.call import Call


class TestSIPClient:
    @pytest.fixture
    def mock_socket(self):
        with patch("sip_client.client.socket") as mock:
            mock_socket = MagicMock()
            mock.socket.return_value = mock_socket
            mock_socket.getsockname.return_value = ("192.168.1.100", 5060)
            yield mock_socket

    @pytest.fixture
    def sip_client(self, mock_socket):
        client = SIPClient(
            host="sip.example.com",
            port=5060,
            username="testuser",
            password="testpass",
            display_name="Test Client",
            user_agent="Test/1.0",
        )
        return client

    def test_init(self, sip_client):
        assert sip_client.host == "sip.example.com"
        assert sip_client.port == 5060
        assert sip_client.username == "testuser"
        assert sip_client.password == "testpass"
        assert sip_client.display_name == "Test Client"
        assert sip_client.user_agent == "Test/1.0"
        assert sip_client.call is None
        assert sip_client.running is False

    def test_get_local_ip(self, sip_client, mock_socket):
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ("192.168.1.100", 5060)
        mock_socket.socket.return_value = mock_socket_instance
        ip = sip_client._get_local_ip()
        assert ip == "192.168.1.100"

    def test_get_local_ip_fallback(self, sip_client):
        with patch("sip_client.client.socket") as mock:
            mock.socket.side_effect = Exception("Network error")
            ip = sip_client._get_local_ip()
            assert ip == "127.0.0.1"

    def test_start(self, sip_client, mock_socket):
        sip_client.start()
        assert sip_client.running is True
        assert sip_client.sock is not None
        assert sip_client._thread is not None
        assert sip_client._thread.is_alive()

    def test_stop(self, sip_client, mock_socket):
        sip_client.start()
        sip_client.stop()
        assert sip_client.running is False
        mock_socket.close.assert_called()

    def test_stop_with_active_call(self, sip_client, mock_socket):
        mock_call = MagicMock()
        mock_call.active = True
        sip_client.call = mock_call
        sip_client.start()
        sip_client.stop()
        mock_call.hangup.assert_called()

    def test_receive_loop_timeout(self, sip_client, mock_socket):
        sip_client.running = True
        mock_socket.recvfrom.side_effect = socket.timeout()
        sip_client.sock = mock_socket
        sip_client._receive_loop()
        assert sip_client.running is True

    def test_receive_loop_error(self, sip_client, mock_socket, caplog):
        sip_client.running = True
        mock_socket.recvfrom.side_effect = Exception("Test error")
        sip_client.sock = mock_socket
        sip_client._receive_loop()
        assert "Error receiving message" in caplog.text

    def test_process_message_invite(self, sip_client, mock_socket):
        message = "INVITE sip:test@sip.example.com SIP/2.0\r\nCall-ID: 123\r\nFrom: <sip:caller@sip.example.com>\r\n\r\n"
        sip_client._process_message(message, ("192.168.1.1", 5060))
        assert sip_client.call is not None
        assert sip_client.call.call_id == "123"

    def test_process_message_bye(self, sip_client, mock_socket):
        mock_call = MagicMock()
        mock_call.active = True
        sip_client.call = mock_call
        message = "BYE sip:test@sip.example.com SIP/2.0\r\nCall-ID: 123\r\n\r\n"
        sip_client._process_message(message, ("192.168.1.1", 5060))
        assert mock_call.active is False

    def test_process_message_cancel(self, sip_client, mock_socket):
        mock_call = MagicMock()
        mock_call.active = True
        sip_client.call = mock_call
        message = "CANCEL sip:test@sip.example.com SIP/2.0\r\nCall-ID: 123\r\n\r\n"
        sip_client._process_message(message, ("192.168.1.1", 5060))
        assert mock_call.active is False

    def test_process_message_notify_dtmf(self, sip_client, mock_socket):
        mock_call = MagicMock()
        mock_call.active = True
        sip_client.call = mock_call
        message = "NOTIFY sip:test@sip.example.com SIP/2.0\r\nContent-Type: application/dtmf-relay\r\n\r\nSignal=1"
        dtmf_received = []
        sip_client.on_dtmf = lambda d: dtmf_received.append(d)
        sip_client._process_message(message, ("192.168.1.1", 5060))
        assert "1" in dtmf_received

    def test_process_message_empty(self, sip_client, mock_socket):
        sip_client._process_message("", ("192.168.1.1", 5060))
        assert sip_client.call is None

    def test_handle_invite_busy(self, sip_client, mock_socket):
        mock_call = MagicMock()
        mock_call.active = True
        sip_client.call = mock_call
        message = "INVITE sip:test@sip.example.com SIP/2.0\r\nCall-ID: 123\r\nFrom: <sip:caller@sip.example.com>\r\n\r\n"
        sip_client._handle_invite(message, ("192.168.1.1", 5060))
        mock_socket.sendto.assert_called()

    def test_handle_invite_callback(self, sip_client, mock_socket):
        callback_called = []
        sip_client.on_incoming_call = lambda c: callback_called.append(c)
        message = "INVITE sip:test@sip.example.com SIP/2.0\r\nCall-ID: 123\r\nFrom: <sip:caller@sip.example.com>\r\n\r\n"
        sip_client._handle_invite(message, ("192.168.1.1", 5060))
        assert len(callback_called) == 1

    def test_send_response(self, sip_client, mock_socket):
        sip_client._send_response(("192.168.1.1", 5060), 200, "OK", "123")
        mock_socket.sendto.assert_called()

    def test_handle_bye_callback(self, sip_client, mock_socket):
        mock_call = MagicMock()
        mock_call.active = True
        sip_client.call = mock_call
        callback_called = []
        sip_client.on_call_ended = lambda r: callback_called.append(r)
        message = "BYE sip:test@sip.example.com SIP/2.0\r\nCall-ID: 123\r\n\r\n"
        sip_client._handle_bye(message, ("192.168.1.1", 5060))
        assert "remote_hangup" in callback_called

    def test_handle_cancel_callback(self, sip_client, mock_socket):
        mock_call = MagicMock()
        mock_call.active = True
        sip_client.call = mock_call
        callback_called = []
        sip_client.on_call_ended = lambda r: callback_called.append(r)
        message = "CANCEL sip:test@sip.example.com SIP/2.0\r\nCall-ID: 123\r\n\r\n"
        sip_client._handle_cancel(message, ("192.168.1.1", 5060))
        assert "cancelled" in callback_called

    def test_handle_notify_no_content(self, sip_client, mock_socket):
        message = "NOTIFY sip:test@sip.example.com SIP/2.0\r\n\r\n"
        sip_client._handle_notify(message, ("192.168.1.1", 5060))

    def test_parse_dtmf_signal(self, sip_client):
        content = "Signal=5\r\nDuration=100"
        digit = sip_client._parse_dtmf(content)
        assert digit == "5"

    def test_parse_dtmf_no_signal(self, sip_client):
        content = "Duration=100"
        digit = sip_client._parse_dtmf(content)
        assert digit is None

    def test_extract_header(self, sip_client):
        message = "Call-ID: 12345\r\nFrom: test\r\n"
        header = sip_client._extract_header(message, "Call-ID")
        assert header == "12345"

    def test_extract_header_not_found(self, sip_client):
        message = "From: test\r\n"
        header = sip_client._extract_header(message, "Call-ID")
        assert header is None

    def test_parse_contact_with_sip(self, sip_client):
        header = "<sip:123456@sip.example.com>"
        contact = sip_client._parse_contact(header)
        assert contact == "123456"

    def test_parse_contact_plain(self, sip_client):
        header = "test@example.com"
        contact = sip_client._parse_contact(header)
        assert contact == "test@example.com"

    def test_make_call_existing(self, sip_client, mock_socket):
        mock_call = MagicMock()
        mock_call.active = True
        sip_client.call = mock_call
        result = sip_client.make_call("123456")
        assert result is None

    def test_make_call(self, sip_client, mock_socket):
        result = sip_client.make_call("123456")
        assert result is not None
        assert isinstance(result, Call)
        assert result.active is False

    def test_answer_call(self, sip_client, mock_socket):
        mock_call = MagicMock()
        sip_client.call = mock_call
        sip_client.answer_call()
        mock_call.answer.assert_called()

    def test_answer_call_no_call(self, sip_client, mock_socket):
        sip_client.call = None
        sip_client.answer_call()

    def test_hangup_call(self, sip_client, mock_socket):
        mock_call = MagicMock()
        sip_client.call = mock_call
        callback_called = []
        sip_client.on_call_ended = lambda r: callback_called.append(r)
        sip_client.hangup_call()
        mock_call.hangup.assert_called()
        assert sip_client.call is None
        assert "local_hangup" in callback_called

    def test_hangup_call_no_call(self, sip_client, mock_socket):
        sip_client.call = None
        sip_client.hangup_call()
