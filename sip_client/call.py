import socket
import threading
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .client import SIPClient

logger = logging.getLogger(__name__)


class Call:
    def __init__(
        self,
        client: "SIPClient",
        remote_addr: tuple,
        call_id: str,
        caller_id: str,
        outgoing: bool = False,
    ):
        self.client = client
        self.remote_addr = remote_addr
        self.call_id = call_id
        self.caller_id = caller_id
        self.outgoing = outgoing
        self.active = False
        self.answered = False
        self.cseq = 1
        self._rtp_port = 10000
        self._rtp_sock: Optional[socket.socket] = None
        self._rtcp_port = 10001
        self._rtcp_sock: Optional[socket.socket] = None

    def invite(self, destination: str) -> None:
        logger.info(f"Sending INVITE to {destination}")
        invite = self._build_invite(destination)
        self.client.sock.sendto(invite.encode(), self.remote_addr)
        self.cseq += 1

    def answer(self) -> None:
        logger.info("Answering call")
        answer = self._build_200_ok()
        self.client.sock.sendto(answer.encode(), self.remote_addr)
        self.active = True
        self.answered = True
        self._start_rtp()

    def hangup(self) -> None:
        logger.info("Sending BYE")
        bye = self._build_bye()
        self.client.sock.sendto(bye.encode(), self.remote_addr)
        self.active = False
        self.answered = False
        self._stop_rtp()

    def _build_invite(self, destination: str) -> str:
        sdp = self._build_sdp()
        invite = f"INVITE sip:{destination}@{self.client.host} SIP/2.0\r\n"
        invite += f"Via: SIP/2.0/UDP {self.client.local_ip}:{self.client.local_port}\r\n"
        invite += f"From: <sip:{self.client.username}@{self.client.host}>\r\n"
        invite += f"To: <sip:{destination}@{self.client.host}>\r\n"
        invite += f"Call-ID: {self.call_id}\r\n"
        invite += f"CSeq: {self.cseq} INVITE\r\n"
        invite += f"Contact: <sip:{self.client.username}@{self.client.local_ip}:{self.client.local_port}>\r\n"
        invite += f"User-Agent: {self.client.user_agent}\r\n"
        invite += "Content-Type: application/sdp\r\n"
        invite += f"Content-Length: {len(sdp)}\r\n\r\n"
        invite += sdp
        return invite

    def _build_200_ok(self) -> str:
        sdp = self._build_sdp()
        response = "SIP/2.0 200 OK\r\n"
        response += f"Via: SIP/2.0/UDP {self.client.local_ip}:{self.client.local_port}\r\n"
        response += f"From: <sip:{self.client.username}@{self.client.host}>\r\n"
        response += f"To: <sip:{self.client.username}@{self.client.host}>\r\n"
        response += f"Call-ID: {self.call_id}\r\n"
        response += f"CSeq: {self.cseq} INVITE\r\n"
        response += f"Contact: <sip:{self.client.username}@{self.client.local_ip}:{self.client.local_port}>\r\n"
        response += f"User-Agent: {self.client.user_agent}\r\n"
        response += "Content-Type: application/sdp\r\n"
        response += f"Content-Length: {len(sdp)}\r\n\r\n"
        response += sdp
        return response

    def _build_bye(self) -> str:
        bye = f"BYE sip:{self.caller_id}@{self.client.host} SIP/2.0\r\n"
        bye += f"Via: SIP/2.0/UDP {self.client.local_ip}:{self.client.local_port}\r\n"
        bye += f"From: <sip:{self.client.username}@{self.client.host}>\r\n"
        bye += f"To: <sip:{self.caller_id}@{self.client.host}>\r\n"
        bye += f"Call-ID: {self.call_id}\r\n"
        bye += f"CSeq: {self.cseq} BYE\r\n"
        bye += f"User-Agent: {self.client.user_agent}\r\n"
        bye += "Content-Length: 0\r\n\r\n"
        return bye

    def _build_sdp(self) -> str:
        sdp = "v=0\r\n"
        sdp += f"o=- 0 0 IN IP4 {self.client.local_ip}\r\n"
        sdp += "s=-\r\n"
        sdp += "c=IN IP4 {0}\r\n".format(self.client.local_ip)
        sdp += "t=0 0\r\n"
        sdp += "m=audio {0} RTP/AVP 0 8 101\r\n".format(self._rtp_port)
        sdp += "a=rtpmap:0 PCMU/8000\r\n"
        sdp += "a=rtpmap:8 PCMA/8000\r\n"
        sdp += "a=rtpmap:101 telephone-event/8000\r\n"
        sdp += "a=fmtp:101 0-15\r\n"
        sdp += "a=sendrecv\r\n"
        return sdp

    def _start_rtp(self) -> None:
        self._rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rtp_sock.bind(("0.0.0.0", self._rtp_port))
        self._rtp_sock.settimeout(0.1)
        self._rtcp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rtcp_sock.bind(("0.0.0.0", self._rtcp_port))
        self._rtcp_sock.settimeout(0.1)
        logger.info(f"RTP started on port {self._rtp_port}")

    def _stop_rtp(self) -> None:
        if self._rtp_sock:
            self._rtp_sock.close()
            self._rtp_sock = None
        if self._rtcp_sock:
            self._rtcp_sock.close()
            self._rtcp_sock = None
        logger.info("RTP stopped")

    def send_dtmf(self, digit: str, duration: int = 100) -> None:
        logger.info(f"Sending DTMF: {digit}")
        rtp_packet = self._build_rtp_dtmf(digit, duration)
        if self._rtp_sock:
            self._rtp_sock.sendto(rtp_packet, self.remote_addr)

    def _build_rtp_dtmf(self, digit: str, duration: int) -> bytes:
        event = int(digit) if digit.isdigit() else 10 + ord(digit.upper()) - ord("A")
        header = bytes([0x80, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        payload = bytes([event, 0x0A, duration >> 8, duration & 0xFF])
        return header + payload
