# SIP-MQTT Client

A production-ready SIP client that connects to a SIP trunk, monitors for incoming calls, and reports events through MQTT. Supports remote call control, DTMF detection, and PulseAudio integration for audio routing.

## Features

- **SIP Trunk Integration**: Connect to any standard SIP trunk provider
- **MQTT Integration**: Real-time call status reporting and remote control
- **Call Control**: Answer, reject, or hangup calls via MQTT commands
- **DTMF Detection**: Detect and report DTMF tones during calls
- **PulseAudio Support**: Route audio through PulseAudio sink/source
- **Event Reporting**: Comprehensive event reporting for all call states
- **Configurable**: YAML-based configuration for all components
- **Tested**: 90%+ code coverage with comprehensive unit tests

## Installation

### Prerequisites

- Python 3.8+
- PyAudio library
- MQTT broker (e.g., Mosquitto)

### Install Dependencies

```bash
# System dependencies (Ubuntu/Debian)
sudo apt-get install python3-pyaudio portaudio19-dev

# Python dependencies
pip install -e .

# For development and testing
pip install -e ".[test]"
```

### Dependencies

| Package | Version | Description |
|---------|---------|-------------|
| paho-mqtt | >=1.6.1 | MQTT client library |
| pyaudio | >=0.2.11 | Audio I/O |
| pyyaml | >=5.4 | YAML configuration |
| numpy | >=1.21.0 | Audio processing |

## Configuration

Create a `config.yaml` file:

```yaml
# SIP Configuration
sip:
  trunk_host: "sip.trunk.provider.com"    # SIP server address
  trunk_port: 5060                         # SIP server port
  username: "sip_user"                     # SIP username
  password: "sip_password"                 # SIP password
  display_name: "SIP Client"               # Display name for caller ID
  user_agent: "SIP-MQTT-Client/0.1"       # User-Agent header
  register: true                           # Enable registration
  register_expiry: 3600                    # Registration expiry (seconds)

# MQTT Configuration
mqtt:
  broker_host: "localhost"                 # MQTT broker address
  broker_port: 1883                        # MQTT broker port
  username: ""                             # MQTT username (optional)
  password: ""                             # MQTT password (optional)
  client_id: "sip-client-001"              # Unique client ID
  topics:
    incoming_call: "sip/call/incoming"     # Incoming call notifications
    call_status: "sip/call/status"         # Call status updates
    call_control: "sip/call/control"       # Call control commands
    dtmf: "sip/dtmf"                       # DTMF events
    audio_control: "sip/audio/control"     # Audio control commands

# Audio Configuration
audio:
  sample_rate: 8000                        # Audio sample rate (Hz)
  channels: 1                              # Audio channels (mono)
  chunk_size: 160                          # Audio buffer size
  pulse_server: "localhost"                # PulseAudio server
  sink_name: "sip_output"                  # Output sink name
  source_name: "sip_input"                 # Input source name

# Logging Configuration
logging:
  level: "INFO"                            # Log level (DEBUG, INFO, WARNING, ERROR)
  file: "sip-mqtt-client.log"              # Log file path
```

## Usage

### Start the Client

```bash
# Using default config.yaml
python main.py

# Using custom config file
python main.py --config /path/to/config.yaml

# Or using the installed command
sip-mqtt-client --config config.yaml
```

### Command Line Options

```
usage: main.py [-h] [-c CONFIG]

SIP-MQTT Client

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Config file path (default: config.yaml)
```

## MQTT API

### Published Topics

#### `sip/call/status`

Call status updates published when call state changes.

**Payload:**
```json
{
  "status": "incoming|answered|ended|hungup|rejected|ready",
  "caller_id": "123456789",
  "call_id": "unique-call-id",
  "timestamp": 1699000000.123
}
```

**Status Values:**
| Status | Description |
|--------|-------------|
| `ready` | Client started and ready to receive calls |
| `incoming` | Incoming call detected |
| `answered` | Call answered |
| `ended` | Call ended (remote party hung up) |
| `hungup` | Call hung up (local party) |
| `rejected` | Call rejected |

#### `sip/dtmf`

DTMF digits detected during active calls.

**Payload:**
```json
{
  "digit": "5",
  "duration": 100,
  "timestamp": 1699000000.123
}
```

### Subscribed Topics

#### `sip/call/control`

Send commands to control active calls.

**Payload:**
```json
{
  "action": "answer|hangup|reject"
}
```

**Actions:**
| Action | Description |
|--------|-------------|
| `answer` | Answer incoming call |
| `hangup` | End active call |
| `reject` | Reject incoming call |

#### `sip/audio/control`

Control audio streaming.

**Payload:**
```json
{
  "action": "start|stop"
}
```

## Examples

### Answer an Incoming Call

```bash
mosquitto_pub -t "sip/call/control" -m '{"action": "answer"}'
```

### Hangup Active Call

```bash
mosquitto_pub -t "sip/call/control" -m '{"action": "hangup"}'
```

### Subscribe to Call Status

```bash
mosquitto_sub -t "sip/call/status" -v
```

### Subscribe to DTMF Events

```bash
mosquitto_sub -t "sip/dtmf" -v
```

### Complete Example Flow

```bash
# Terminal 1: Monitor all events
mosquitto_sub -t "sip/#" -v

# Terminal 2: Send commands
# When incoming call arrives:
mosquitto_pub -t "sip/call/control" -m '{"action": "answer"}'

# To hangup:
mosquitto_pub -t "sip/call/control" -m '{"action": "hangup"}'
```

## Architecture

```
┌─────────────┐      SIP       ┌─────────────┐
│  SIP Trunk  │◄──────────────►│  SIP Client │
│  Provider   │                │             │
└─────────────┘                └──────┬──────┘
                                      │
                                      │ MQTT
                                      │
                               ┌──────▼──────┐
                               │ MQTT Broker │
                               │ (Mosquitto) │
                               └──────┬──────┘
                                      │
                                      │ MQTT
                                      │
                               ┌──────▼──────┐
                               │   Control   │
                               │   Server    │
                               └─────────────┘

Audio Flow:
┌─────────────┐     RTP      ┌─────────────┐     PCM     ┌─────────────┐
│  Remote     │◄────────────►│  SIP Client │◄───────────►│ PulseAudio  │
│  Party      │              │             │             │  Sink/Source│
└─────────────┘              └─────────────┘             └─────────────┘
```

## Project Structure

```
sip-mqtt-client/
├── main.py                 # Application entry point
├── config.yaml             # Configuration file
├── pyproject.toml          # Project metadata and dependencies
├── pytest.ini              # Pytest configuration
├── README.md               # This file
├── sip_client/
│   ├── __init__.py
│   ├── client.py           # SIP client implementation
│   └── call.py             # Call handling
├── mqtt_handler/
│   ├── __init__.py
│   └── handler.py          # MQTT communication
├── audio/
│   ├── __init__.py
│   └── pulseaudio.py       # PulseAudio integration
└── tests/
    ├── __init__.py
    ├── test_sip_client.py
    ├── test_call.py
    ├── test_mqtt_handler.py
    ├── test_audio.py
    └── test_main.py
```

## Testing

### Run Tests

```bash
# Run all tests with coverage
pytest

# Run with HTML coverage report
pytest --cov-report=html

# Run specific test file
pytest tests/test_sip_client.py

# Run specific test
pytest tests/test_sip_client.py::TestSIPClient::test_init
```

### Coverage Requirements

The project enforces 90% code coverage:

```bash
pytest --cov-fail-under=90
```

### View Coverage Report

```bash
# Terminal report
pytest --cov-report=term-missing

# HTML report (open in browser)
pytest --cov-report=html
firefox htmlcov/index.html
```

## Troubleshooting

### Common Issues

**PyAudio Installation Failed**
```bash
# Install PortAudio development files
sudo apt-get install portaudio19-dev
pip install pyaudio
```

**Cannot Connect to MQTT Broker**
- Verify broker is running: `systemctl status mosquitto`
- Check firewall rules: `sudo ufw allow 1883`
- Verify configuration: `mqtt.broker_host`

**No Audio**
- Check PulseAudio is running: `pulseaudio --check`
- Verify sink/source names: `pactl list sinks`
- Check audio permissions

**SIP Registration Failed**
- Verify credentials in config.yaml
- Check network connectivity to SIP trunk
- Review logs for error details

### Logging

Enable debug logging for troubleshooting:

```yaml
logging:
  level: "DEBUG"
  file: "sip-mqtt-client.log"
```

View logs:
```bash
tail -f sip-mqtt-client.log
```

## API Reference

### SIPClient

```python
from sip_client import SIPClient

client = SIPClient(
    host="sip.example.com",
    port=5060,
    username="user",
    password="pass",
    display_name="My Client",
    user_agent="Client/1.0"
)

# Callbacks
client.on_incoming_call = lambda call: print(f"Call from {call.caller_id}")
client.on_call_ended = lambda reason: print(f"Call ended: {reason}")
client.on_dtmf = lambda digit: print(f"DTMF: {digit}")

# Start/Stop
client.start()
client.stop()

# Call control
client.answer_call()
client.hangup_call()
```

### Call

```python
from sip_client import Call

# Call properties
call.caller_id      # Caller ID string
call.call_id        # Unique call identifier
call.active         # Boolean: call is active
call.answered       # Boolean: call is answered
call.outgoing       # Boolean: outgoing call

# Call methods
call.answer()       # Answer the call
call.hangup()       # End the call
call.send_dtmf("5") # Send DTMF digit
```

### MQTTHandler

```python
from mqtt_handler import MQTTHandler

handler = MQTTHandler(
    broker_host="localhost",
    broker_port=1883,
    client_id="my-client"
)

# Set topics
handler.set_topics({
    "call_status": "sip/call/status",
    "call_control": "sip/call/control",
    "dtmf": "sip/dtmf"
})

# Callbacks
handler.on_call_control = lambda p: print(f"Control: {p}")

# Publish
handler.publish_call_status("incoming", "123456", "call-123")
handler.publish_dtmf("5", 100)
```

### PulseAudioHandler

```python
from audio import PulseAudioHandler

audio = PulseAudioHandler(
    sample_rate=8000,
    channels=1,
    chunk_size=160,
    sink_name="sip_output",
    source_name="sip_input"
)

# Start/Stop
audio.start()
audio.stop()

# Audio I/O
audio.write_audio(data)           # Play audio
audio.on_audio_input = callback   # Receive audio
```

## Security Considerations

- Store SIP credentials securely (consider environment variables)
- Use TLS for MQTT connections in production
- Restrict MQTT topic access with ACLs
- Keep the client behind a firewall
- Regularly update dependencies

## License

Beer-Ware License - See [LICENSE](LICENSE) file for details.

If you find this software useful and we meet someday, you can buy me a beer! 🍺

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## Support

For issues and feature requests, please open an issue on the project repository.
