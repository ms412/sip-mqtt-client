import pytest
import socket
from unittest.mock import Mock, patch, MagicMock
from sip_client.call import Call


class TestCall:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.host = "sip.example.com"
        client.username = "testuser"
        client.local_ip = "192.168.1.100"
        client.local_port = 5060
        client.user_agent = "Test/1.0"
        client.sock = MagicMock()
        return client

    @pytest.fixture
    def call(self, mock_client):
        return Call(
            client=mock_client,
            remote_addr=("192.168.1.1", 5060),
            call_id="test-call-123",
            caller_id="123456",
            outgoing=False,
        )

    def test_init(self, call):
        assert call.call_id == "test-call-123"
        assert call.caller_id == "123456"
        assert call.outgoing is False
        assert call.active is False
        assert call.answered is False
        assert call.cseq == 1

    def test_invite(self, call):
        call.invite("789012")
        call.client.sock.sendto.assert_called()

    def test_answer(self, call):
        call.answer()
        assert call.active is True
        assert call.answered is True
        call.client.sock.sendto.assert_called()

    def test_hangup(self, call):
        call.active = True
        call.answered = True
        call.hangup()
        assert call.active is False
        assert call.answered is False
        call.client.sock.sendto.assert_called()

    def test_build_invite(self, call):
        invite = call._build_invite("789012")
        assert "INVITE sip:789012@sip.example.com SIP/2.0" in invite
        assert "Call-ID: test-call-123" in invite
        assert "application/sdp" in invite

    def test_build_200_ok(self, call):
        response = call._build_200_ok()
        assert "SIP/2.0 200 OK" in response
        assert "Call-ID: test-call-123" in response
        assert "application/sdp" in response

    def test_build_bye(self, call):
        bye = call._build_bye()
        assert "BYE sip:123456@sip.example.com SIP/2.0" in bye
        assert "Call-ID: test-call-123" in bye

    def test_build_sdp(self, call):
        sdp = call._build_sdp()
        assert "v=0" in sdp
        assert "m=audio" in sdp
        assert "rtpmap:0 PCMU/8000" in sdp
        assert "rtpmap:8 PCMA/8000" in sdp
        assert "rtpmap:101 telephone-event/8000" in sdp
        assert "a=sendrecv" in sdp

    def test_start_rtp(self, call):
        with patch("sip_client.call.socket") as mock_socket:
            call._start_rtp()
            assert call._rtp_sock is not None
            assert call._rtcp_sock is not None
            assert call._rtp_port == 10000
            assert call._rtcp_port == 10001

    def test_stop_rtp(self, call):
        mock_rtp_sock = MagicMock()
        mock_rtcp_sock = MagicMock()
        call._rtp_sock = mock_rtp_sock
        call._rtcp_sock = mock_rtcp_sock
        call._stop_rtp()
        mock_rtp_sock.close.assert_called()
        mock_rtcp_sock.close.assert_called()
        assert call._rtp_sock is None
        assert call._rtcp_sock is None

    def test_stop_rtp_no_sockets(self, call):
        call._rtp_sock = None
        call._rtcp_sock = None
        call._stop_rtp()

    def test_send_dtmf(self, call):
        with patch.object(call, "_build_rtp_dtmf") as mock_build:
            mock_build.return_value = b"test"
            mock_rtp_sock = MagicMock()
            call._rtp_sock = mock_rtp_sock
            call.send_dtmf("5", 100)
            mock_build.assert_called_with("5", 100)
            mock_rtp_sock.sendto.assert_called()

    def test_send_dtmf_no_socket(self, call):
        call._rtp_sock = None
        call.send_dtmf("5", 100)

    def test_build_rtp_dtmf_digit(self, call):
        packet = call._build_rtp_dtmf("5", 100)
        assert isinstance(packet, bytes)
        assert len(packet) > 0

    def test_build_rtp_dtmf_letter(self, call):
        packet = call._build_rtp_dtmf("A", 100)
        assert isinstance(packet, bytes)
        assert len(packet) > 0

    def test_build_rtp_dtmf_star(self, call):
        packet = call._build_rtp_dtmf("*", 100)
        assert isinstance(packet, bytes)
        assert len(packet) > 0

    def test_build_rtp_dtmf_hash(self, call):
        packet = call._build_rtp_dtmf("#", 100)
        assert isinstance(packet, bytes)
        assert len(packet) > 0

    def test_outgoing_call(self, mock_client):
        call = Call(
            client=mock_client,
            remote_addr=("192.168.1.1", 5060),
            call_id="outgoing-123",
            caller_id="789012",
            outgoing=True,
        )
        assert call.outgoing is True
        call.invite("789012")
        mock_client.sock.sendto.assert_called()
