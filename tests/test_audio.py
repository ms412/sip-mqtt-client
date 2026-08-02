import pytest
from unittest.mock import Mock, patch, MagicMock
from audio.pulseaudio import PulseAudioHandler


class TestPulseAudioHandler:
    @pytest.fixture
    def audio_handler(self):
        return PulseAudioHandler()

    @pytest.fixture
    def mock_pyaudio(self):
        with patch("audio.pulseaudio.pyaudio") as mock:
            mock_pa = MagicMock()
            mock.PyAudio.return_value = mock_pa
            yield mock

    def test_init(self, audio_handler):
        assert audio_handler.sample_rate == 8000
        assert audio_handler.channels == 1

    def test_start_success(self, audio_handler, mock_pyaudio):
        result = audio_handler.start()
        assert result is True

    def test_stop(self, audio_handler, mock_pyaudio):
        audio_handler.pa = MagicMock()
        audio_handler.running = False
        audio_handler.stop()
