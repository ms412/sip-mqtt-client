import socket
import threading
import logging
from typing import Optional, Callable
from .call import Call

logger = logging.getLogger(__name__)


class SIPClient:
    def __init__(
        self,
        host: str,
        port: int = 5060,
        username: str = "",
        password: str = "",
        display_name: str = "SIP Client",
        user_agent: str = "SIP-MQTT-Client/0.1",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.display_name = display_name
        self.user_agent = user_agent
        self.local_ip = self._get_local_ip()
        self.local_port = 5060
        self.sock: Optional[socket.socket] = None
        self.call: Optional[Call] = None
        self.running = False
        self.on_incoming_call: Optional[Callable] = None
        self.on_call_ended: Optional[Callable] = None
        self.on_dtmf: Optional[Callable] = None
        self._thread: Optional[threading.Thread] = None

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.host, self.port))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", self.local_port))
        self.sock.settimeout(1.0)
        self.running = True
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()
        logger.info(f"SIP client started on {self.local_ip}:{self.local_port}")

    def stop(self) -> None:
        self.running = False
        if self.call:
            self.call.hangup()
        if self.sock:
            self.sock.close()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("SIP client stopped")

    def _receive_loop(self) -> None:
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                message = data.decode("utf-8", errors="ignore")
                self._process_message(message, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving message: {e}")

    def _process_message(self, message: str, addr: tuple) -> None:
        lines = message.split("\r\n")
        if not lines:
            return

        first_line = lines[0]
        if first_line.startswith("INVITE"):
            self._handle_invite(message, addr)
        elif first_line.startswith("BYE"):
            self._handle_bye(message, addr)
        elif first_line.startswith("ACK"):
            pass
        elif first_line.startswith("CANCEL"):
            self._handle_cancel(message, addr)
        elif "SIP/2.0" in first_line:
            self._handle_response(message, addr)
        elif first_line.startswith("NOTIFY"):
            self._handle_notify(message, addr)

    def _handle_invite(self, message: str, addr: tuple) -> None:
        logger.info("Received INVITE")
        call_id = self._extract_header(message, "Call-ID")
        from_header = self._extract_header(message, "From")
        caller_id = self._parse_contact(from_header) if from_header else "Unknown"

        if self.call and self.call.active:
            self._send_response(addr, 486, "Busy Here", call_id)
            return

        self.call = Call(self, addr, call_id, caller_id)
        self._send_response(addr, 100, "Trying", call_id)
        self._send_response(addr, 180, "Ringing", call_id)

        if self.on_incoming_call:
            self.on_incoming_call(self.call)

    def _send_response(self, addr: tuple, code: int, reason: str, call_id: str) -> None:
        response = f"SIP/2.0 {code} {reason}\r\n"
        response += f"Via: SIP/2.0/UDP {self.host}:{self.port}\r\n"
        response += f"From: <sip:{self.username}@{self.host}>\r\n"
        response += f"To: <sip:{self.username}@{self.host}>\r\n"
        response += f"Call-ID: {call_id}\r\n"
        response += "CSeq: 1 INVITE\r\n"
        response += f"Server: {self.user_agent}\r\n"
        response += "Content-Length: 0\r\n\r\n"
        self.sock.sendto(response.encode(), addr)

    def _handle_bye(self, message: str, addr: tuple) -> None:
        logger.info("Received BYE")
        if self.call:
            self.call.active = False
            if self.on_call_ended:
                self.on_call_ended("remote_hangup")
            self.call = None

    def _handle_cancel(self, message: str, addr: tuple) -> None:
        logger.info("Received CANCEL")
        if self.call:
            self.call.active = False
            if self.on_call_ended:
                self.on_call_ended("cancelled")
            self.call = None

    def _handle_response(self, message: str, addr: tuple) -> None:
        pass

    def _handle_notify(self, message: str, addr: tuple) -> None:
        content = message.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in message else ""
        if "application/dtmf-relay" in message or "telephone-event" in message:
            dtmf_digit = self._parse_dtmf(content)
            if dtmf_digit and self.on_dtmf:
                self.on_dtmf(dtmf_digit)

    def _parse_dtmf(self, content: str) -> Optional[str]:
        for line in content.split("\r\n"):
            if line.startswith("Signal="):
                return line.split("=")[1].strip()
        return None

    def _extract_header(self, message: str, header: str) -> Optional[str]:
        for line in message.split("\r\n"):
            if line.lower().startswith(header.lower() + ":"):
                return line.split(":", 1)[1].strip()
        return None

    def _parse_contact(self, header: str) -> str:
        if "<" in header and ">" in header:
            return header.split("<")[1].split(">")[0].split("@")[0].replace("sip:", "")
        return header

    def make_call(self, destination: str) -> Optional[Call]:
        if self.call and self.call.active:
            logger.warning("Call already active")
            return None

        call_id = f"{socket.gethostname()}-{threading.current_thread().ident}"
        self.call = Call(self, (self.host, self.port), call_id, destination, outgoing=True)
        self.call.invite(destination)
        return self.call

    def answer_call(self) -> None:
        if self.call:
            self.call.answer()

    def hangup_call(self) -> None:
        if self.call:
            self.call.hangup()
            if self.on_call_ended:
                self.on_call_ended("local_hangup")
            self.call = None
