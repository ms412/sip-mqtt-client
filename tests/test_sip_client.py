import pytest
from unittest.mock import Mock, patch, MagicMock
from sip_client.client import SIPClient


class TestSIPClient:
    @pytest.fixture
    def sip_client(self):
        with patch("sip_client.client.socket"):
            client = SIPClient(
                host="sip.example.com",
                port=5060,
                username="testuser",
                password="testpass",
            )
            return client

    def test_init(self, sip_client):
        assert sip_client.host == "sip.example.com"
        assert sip_client.username == "testuser"

    def test_get_local_ip(self, sip_client):
        with patch("sip_client.client.socket") as mock:
            mock.socket.return_value.getsockname.return_value = ("192.168.1.100", 5060)
            ip = sip_client._get_local_ip()
            assert ip == "192.168.1.100"
