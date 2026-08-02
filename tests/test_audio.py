import pytest
from unittest.mock import Mock, patch, MagicMock
from audio.pulseaudio import PulseAudioHandler


class TestPulseAudioHandler:
    @pytest.fixture
    def audio_handler(self):
        handler = PulseAudioHandler(
            sample_rate=8000,
            channels=1,
            chunk_size=160,
            pulse_server="localhost",
            sink_name="sip_output",
            source_name="sip_input",
        )
        return handler

    @pytest.fixture
    def mock_pyaudio(self):
        with patch("audio.pulseaudio.pyaudio") as mock:
            mock_pa = MagicMock()
            mock.PyAudio.return_value = mock_pa
            mock_pa.get_device_count.return_value = 2
            mock_pa.get_device_info_by_index.return_value = {
                "name": "sip_input",
                "maxInputChannels": 1,
                "maxOutputChannels": 1,
            }
            yield mock

    def test_init(self, audio_handler):
        assert audio_handler.sample_rate == 8000
        assert audio_handler.channels == 1
        assert audio_handler.chunk_size == 160
        assert audio_handler.pulse_server == "localhost"
        assert audio_handler.sink_name == "sip_output"
        assert audio_handler.source_name == "sip_input"
        assert audio_handler.pa is None
        assert audio_handler.running is False

    def test_start_success(self, audio_handler, mock_pyaudio):
        result = audio_handler.start()
        assert result is True
        assert audio_handler.running is True
        assert audio_handler.pa is not None

    def test_start_pyaudio_not_installed(self):
        with patch("audio.pulseaudio.pyaudio", None):
            handler = PulseAudioHandler()
            result = handler.start()
            assert result is False

    def test_start_failure(self, audio_handler):
        with patch("audio.pulseaudio.pyaudio") as mock:
            mock.PyAudio.side_effect = Exception("Audio device error")
            result = audio_handler.start()
            assert result is False

    def test_stop(self, audio_handler, mock_pyaudio):
        mock_stream = MagicMock()
        audio_handler.input_stream = mock_stream
        audio_handler.output_stream = mock_stream
        audio_handler.pa = MagicMock()
        audio_handler.running = True
        audio_handler._input_thread = MagicMock()
        audio_handler._output_thread = MagicMock()
        audio_handler.stop()
        assert audio_handler.running is False
        mock_stream.stop_stream.assert_called()
        mock_stream.close.assert_called()
        audio_handler.pa.terminate.assert_called()

    def test_stop_no_streams(self, audio_handler):
        audio_handler.input_stream = None
        audio_handler.output_stream = None
        audio_handler.pa = None
        audio_handler.running = False
        audio_handler.stop()

    def test_start_input(self, audio_handler, mock_pyaudio):
        mock_pa = mock_pyaudio.PyAudio.return_value
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        audio_handler.pa = mock_pa
        audio_handler._start_input()
        assert audio_handler.input_stream is not None
        assert audio_handler._input_thread is not None

    def test_start_input_failure(self, audio_handler, mock_pyaudio):
        mock_pa = mock_pyaudio.PyAudio.return_value
        mock_pa.open.side_effect = Exception("Input error")
        audio_handler.pa = mock_pa
        audio_handler._start_input()
        assert audio_handler.input_stream is None

    def test_start_output(self, audio_handler, mock_pyaudio):
        mock_pa = mock_pyaudio.PyAudio.return_value
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        audio_handler.pa = mock_pa
        audio_handler._start_output()
        assert audio_handler.output_stream is not None
        assert audio_handler._output_thread is not None

    def test_start_output_failure(self, audio_handler, mock_pyaudio):
        mock_pa = mock_pyaudio.PyAudio.return_value
        mock_pa.open.side_effect = Exception("Output error")
        audio_handler.pa = mock_pa
        audio_handler._start_output()
        assert audio_handler.output_stream is None

    def test_get_device_index_input(self, audio_handler, mock_pyaudio):
        mock_pa = mock_pyaudio.PyAudio.return_value
        mock_pa.get_device_count.return_value = 2
        mock_pa.get_device_info_by_index.side_effect = [
            {"name": "sip_input", "maxInputChannels": 1, "maxOutputChannels": 0},
            {"name": "sip_output", "maxInputChannels": 0, "maxOutputChannels": 1},
        ]
        audio_handler.pa = mock_pa
        index = audio_handler._get_device_index("sip_input", input=True)
        assert index == 0

    def test_get_device_index_output(self, audio_handler, mock_pyaudio):
        mock_pa = mock_pyaudio.PyAudio.return_value
        mock_pa.get_device_count.return_value = 2
        mock_pa.get_device_info_by_index.side_effect = [
            {"name": "sip_input", "maxInputChannels": 1, "maxOutputChannels": 0},
            {"name": "sip_output", "maxInputChannels": 0, "maxOutputChannels": 1},
        ]
        audio_handler.pa = mock_pa
        index = audio_handler._get_device_index("sip_output", input=False)
        assert index == 1

    def test_get_device_index_not_found(self, audio_handler, mock_pyaudio):
        mock_pa = mock_pyaudio.PyAudio.return_value
        mock_pa.get_device_count.return_value = 1
        mock_pa.get_device_info_by_index.return_value = {
            "name": "other_device",
            "maxInputChannels": 1,
            "maxOutputChannels": 1,
        }
        audio_handler.pa = mock_pa
        index = audio_handler._get_device_index("sip_input", input=True)
        assert index is None

    def test_get_device_index_no_pa(self, audio_handler):
        audio_handler.pa = None
        index = audio_handler._get_device_index("sip_input", input=True)
        assert index is None

    def test_get_device_index_exception(self, audio_handler, mock_pyaudio):
        mock_pa = mock_pyaudio.PyAudio.return_value
        mock_pa.get_device_count.return_value = 2
        mock_pa.get_device_info_by_index.side_effect = Exception("Device error")
        audio_handler.pa = mock_pa
        index = audio_handler._get_device_index("sip_input", input=True)
        assert index is None

    def test_input_loop(self, audio_handler, mock_pyaudio):
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"test audio data"
        audio_handler.input_stream = mock_stream
        audio_handler.running = True
        callback_data = []
        audio_handler.on_audio_input = lambda d: callback_data.append(d)
        audio_handler._input_loop()
        assert len(callback_data) > 0
        assert callback_data[0] == b"test audio data"

    def test_input_loop_error(self, audio_handler, mock_pyaudio, caplog):
        mock_stream = MagicMock()
        mock_stream.read.side_effect = Exception("Read error")
        audio_handler.input_stream = mock_stream
        audio_handler.running = True
        audio_handler._input_loop()
        assert "Input error" in caplog.text

    def test_input_loop_not_running(self, audio_handler):
        audio_handler.input_stream = MagicMock()
        audio_handler.running = False
        audio_handler._input_loop()

    def test_output_loop(self, audio_handler, mock_pyaudio):
        mock_stream = MagicMock()
        audio_handler.output_stream = mock_stream
        audio_handler.running = True
        audio_handler._audio_queue.put(b"test output data")
        audio_handler._output_loop()
        mock_stream.write.assert_called_with(b"test output data")

    def test_output_loop_empty_queue(self, audio_handler, mock_pyaudio):
        mock_stream = MagicMock()
        audio_handler.output_stream = mock_stream
        audio_handler.running = False
        audio_handler._output_loop()
        mock_stream.write.assert_not_called()

    def test_output_loop_error(self, audio_handler, mock_pyaudio, caplog):
        mock_stream = MagicMock()
        mock_stream.write.side_effect = Exception("Write error")
        audio_handler.output_stream = mock_stream
        audio_handler.running = True
        audio_handler._audio_queue.put(b"test data")
        audio_handler._output_loop()
        assert "Output error" in caplog.text

    def test_write_audio(self, audio_handler):
        audio_handler.running = True
        audio_handler.write_audio(b"test data")
        assert not audio_handler._audio_queue.empty()
        data = audio_handler._audio_queue.get()
        assert data == b"test data"

    def test_write_audio_not_running(self, audio_handler):
        audio_handler.running = False
        audio_handler.write_audio(b"test data")
        assert audio_handler._audio_queue.empty()

    def test_connect_rtp(self, audio_handler, mock_pyaudio):
        mock_rtp_socket = MagicMock()
        audio_handler.connect_rtp(mock_rtp_socket)
        assert audio_handler.on_audio_input is not None
        audio_handler.on_audio_input(b"test data")
        mock_rtp_socket.sendto.assert_called()

    def test_send_to_rtp(self, audio_handler):
        mock_rtp_socket = MagicMock()
        mock_rtp_socket.remote_addr = ("192.168.1.1", 10000)
        audio_handler.running = True
        audio_handler._send_to_rtp(mock_rtp_socket, b"test data")
        mock_rtp_socket.sendto.assert_called_with(b"test data", ("192.168.1.1", 10000))

    def test_send_to_rtp_not_running(self, audio_handler):
        mock_rtp_socket = MagicMock()
        audio_handler.running = False
        audio_handler._send_to_rtp(mock_rtp_socket, b"test data")
        mock_rtp_socket.sendto.assert_not_called()

    def test_send_to_rtp_error(self, audio_handler, caplog):
        mock_rtp_socket = MagicMock()
        mock_rtp_socket.sendto.side_effect = Exception("Send error")
        mock_rtp_socket.remote_addr = ("192.168.1.1", 10000)
        audio_handler.running = True
        audio_handler._send_to_rtp(mock_rtp_socket, b"test data")
        assert "Failed to send audio to RTP" in caplog.text
