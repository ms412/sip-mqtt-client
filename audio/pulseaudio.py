import logging
import threading
import queue
from typing import Optional, Callable

try:
    import pyaudio
except ImportError:
    pyaudio = None

logger = logging.getLogger(__name__)


class PulseAudioHandler:
    def __init__(
        self,
        sample_rate: int = 8000,
        channels: int = 1,
        chunk_size: int = 160,
        pulse_server: str = "localhost",
        sink_name: str = "sip_output",
        source_name: str = "sip_input",
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.pulse_server = pulse_server
        self.sink_name = sink_name
        self.source_name = source_name

        self.pa: Optional[pyaudio.PyAudio] = None
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None
        self.running = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._input_thread: Optional[threading.Thread] = None
        self._output_thread: Optional[threading.Thread] = None

        self.on_audio_input: Optional[Callable[[bytes], None]] = None

    def start(self) -> bool:
        if pyaudio is None:
            logger.error("PyAudio not installed")
            return False

        try:
            self.pa = pyaudio.PyAudio()
            self.running = True
            self._start_input()
            self._start_output()
            logger.info("PulseAudio handler started")
            return True
        except Exception as e:
            logger.error(f"Failed to start PulseAudio: {e}")
            return False

    def stop(self) -> None:
        self.running = False

        if self._input_thread:
            self._input_thread.join(timeout=2.0)
        if self._output_thread:
            self._output_thread.join(timeout=2.0)

        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        if self.pa:
            self.pa.terminate()

        logger.info("PulseAudio handler stopped")

    def _start_input(self) -> None:
        try:
            self.input_stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self._get_device_index(self.source_name, input=True),
            )
            self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
            self._input_thread.start()
        except Exception as e:
            logger.error(f"Failed to start input stream: {e}")
            self.input_stream = None

    def _start_output(self) -> None:
        try:
            self.output_stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                output_device_index=self._get_device_index(self.sink_name, input=False),
            )
            self._output_thread = threading.Thread(target=self._output_loop, daemon=True)
            self._output_thread.start()
        except Exception as e:
            logger.error(f"Failed to start output stream: {e}")
            self.output_stream = None

    def _get_device_index(self, device_name: str, input: bool) -> Optional[int]:
        if self.pa is None:
            return None

        for i in range(self.pa.get_device_count()):
            try:
                info = self.pa.get_device_info_by_index(i)
                if device_name.lower() in info["name"].lower():
                    if input and info["maxInputChannels"] > 0:
                        return i
                    elif not input and info["maxOutputChannels"] > 0:
                        return i
            except Exception:
                continue
        return None

    def _input_loop(self) -> None:
        while self.running and self.input_stream:
            try:
                data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                if self.on_audio_input:
                    self.on_audio_input(data)
            except Exception as e:
                if self.running:
                    logger.error(f"Input error: {e}")
                break

    def _output_loop(self) -> None:
        while self.running and self.output_stream:
            try:
                data = self._audio_queue.get(timeout=0.1)
                self.output_stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Output error: {e}")
                break

    def write_audio(self, data: bytes) -> None:
        if self.running:
            self._audio_queue.put(data)

    def connect_rtp(self, rtp_socket) -> None:
        def on_rtp_audio(data: bytes):
            self.write_audio(data)

        self.on_audio_input = lambda data: self._send_to_rtp(rtp_socket, data)

    def _send_to_rtp(self, rtp_socket, data: bytes) -> None:
        if rtp_socket and self.running:
            try:
                rtp_socket.sendto(data, rtp_socket.remote_addr)
            except Exception as e:
                logger.error(f"Failed to send audio to RTP: {e}")
