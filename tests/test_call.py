import pytest
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
        return Call(mock_client, ("192.168.1.1", 5060), "test-123", "123456")

    def test_init(self, call):
        assert call.call_id == "test-123"
        assert call.caller_id == "123456"
        assert call.active is False

    def test_build_sdp(self, call):
        sdp = call._build_sdp()
        assert "v=0" in sdp
        assert "m=audio" in sdp
