# Configuration Reference

Complete configuration reference for SIP-MQTT Client.

## Configuration File

The client uses YAML configuration. Default location: `config.yaml`

## SIP Configuration

```yaml
sip:
  trunk_host: string        # Required: SIP server hostname or IP
  trunk_port: integer       # Required: SIP server port (default: 5060)
  username: string          # Required: SIP username/extension
  password: string          # Required: SIP password
  display_name: string      # Optional: Caller ID name (default: "SIP Client")
  user_agent: string        # Optional: User-Agent header (default: "SIP-MQTT-Client/0.1")
  register: boolean         # Optional: Enable registration (default: true)
  register_expiry: integer  # Optional: Registration expiry in seconds (default: 3600)
```

### SIP Configuration Examples

**Basic Configuration**
```yaml
sip:
  trunk_host: "sip.provider.com"
  trunk_port: 5060
  username: "1001"
  password: "secret123"
```

**With Custom Display Name**
```yaml
sip:
  trunk_host: "sip.provider.com"
  username: "1001"
  password: "secret123"
  display_name: "Office Phone"
  user_agent: "MyClient/1.0"
```

**Without Registration**
```yaml
sip:
  trunk_host: "sip.provider.com"
  username: "1001"
  password: "secret123"
  register: false
```

## MQTT Configuration

```yaml
mqtt:
  broker_host: string       # Required: MQTT broker hostname or IP
  broker_port: integer      # Required: MQTT broker port (default: 1883)
  username: string          # Optional: MQTT username (default: "")
  password: string          # Optional: MQTT password (default: "")
  client_id: string         # Required: Unique client identifier
  topics:
    incoming_call: string   # Optional: Topic for incoming calls (default: "sip/call/incoming")
    call_status: string     # Optional: Topic for call status (default: "sip/call/status")
    call_control: string    # Optional: Topic for call control (default: "sip/call/control")
    dtmf: string            # Optional: Topic for DTMF events (default: "sip/dtmf")
    audio_control: string   # Optional: Topic for audio control (default: "sip/audio/control")
```

### MQTT Configuration Examples

**Local Broker Without Auth**
```yaml
mqtt:
  broker_host: "localhost"
  broker_port: 1883
  client_id: "sip-client-001"
```

**Remote Broker With Auth**
```yaml
mqtt:
  broker_host: "mqtt.example.com"
  broker_port: 1883
  username: "mqtt_user"
  password: "mqtt_pass"
  client_id: "sip-client-001"
```

**Custom Topics**
```yaml
mqtt:
  broker_host: "localhost"
  client_id: "sip-client-001"
  topics:
    call_status: "telephony/status"
    call_control: "telephony/control"
    dtmf: "telephony/dtmf"
```

## Audio Configuration

```yaml
audio:
  sample_rate: integer      # Optional: Audio sample rate in Hz (default: 8000)
  channels: integer         # Optional: Number of channels (default: 1)
  chunk_size: integer       # Optional: Buffer size in samples (default: 160)
  pulse_server: string      # Optional: PulseAudio server (default: "localhost")
  sink_name: string         # Optional: Output sink name (default: "sip_output")
  source_name: string       # Optional: Input source name (default: "sip_input")
```

### Audio Configuration Examples

**Default Telephony Settings**
```yaml
audio:
  sample_rate: 8000
  channels: 1
  chunk_size: 160
```

**High Quality Audio**
```yaml
audio:
  sample_rate: 16000
  channels: 1
  chunk_size: 320
```

**Custom PulseAudio Devices**
```yaml
audio:
  pulse_server: "tcp:192.168.1.100:4713"
  sink_name: "usb-audio-device"
  source_name: "usb-audio-device"
```

## Logging Configuration

```yaml
logging:
  level: string             # Optional: Log level (default: "INFO")
  file: string              # Optional: Log file path (default: "sip-mqtt-client.log")
```

### Log Levels

| Level | Description |
|-------|-------------|
| DEBUG | Detailed debugging information |
| INFO | General operational messages |
| WARNING | Warning conditions |
| ERROR | Error conditions |
| CRITICAL | Critical errors |

### Logging Examples

**Development Logging**
```yaml
logging:
  level: "DEBUG"
  file: "debug.log"
```

**Production Logging**
```yaml
logging:
  level: "WARNING"
  file: "/var/log/sip-mqtt-client.log"
```

**Disable File Logging**
```yaml
logging:
  level: "INFO"
```

## Complete Configuration Examples

### Home Office Setup

```yaml
sip:
  trunk_host: "sip.provider.com"
  trunk_port: 5060
  username: "1001"
  password: "secure_password"
  display_name: "Home Office"

mqtt:
  broker_host: "192.168.1.100"
  broker_port: 1883
  client_id: "home-office-sip"
  topics:
    call_status: "home/phone/status"
    call_control: "home/phone/control"
    dtmf: "home/phone/dtmf"

audio:
  sample_rate: 8000
  channels: 1
  chunk_size: 160
  sink_name: "alsa_output.usb_audio"
  source_name: "alsa_input.usb_audio"

logging:
  level: "INFO"
  file: "home-office.log"
```

### Enterprise Deployment

```yaml
sip:
  trunk_host: "sip.enterprise.com"
  trunk_port: 5060
  username: "2001"
  password: "enterprise_secret"
  display_name: "Conference Room A"
  user_agent: "Enterprise-SIP/1.0"
  register: true
  register_expiry: 7200

mqtt:
  broker_host: "mqtt.enterprise.com"
  broker_port: 8883
  username: "sip_client"
  password: "mqtt_secret"
  client_id: "conf-room-a-001"
  topics:
    call_status: "enterprise/telephony/conf-a/status"
    call_control: "enterprise/telephony/conf-a/control"
    dtmf: "enterprise/telephony/conf-a/dtmf"
    audio_control: "enterprise/telephony/conf-a/audio"

audio:
  sample_rate: 8000
  channels: 1
  chunk_size: 160
  pulse_server: "tcp:audio-server.enterprise.com:4713"
  sink_name: "conference_room_speaker"
  source_name: "conference_room_mic"

logging:
  level: "WARNING"
  file: "/var/log/sip-mqtt-client-conf-a.log"
```

### Development/Testing

```yaml
sip:
  trunk_host: "localhost"
  trunk_port: 5060
  username: "test"
  password: "test"
  display_name: "Test Client"

mqtt:
  broker_host: "localhost"
  broker_port: 1883
  client_id: "test-client"

audio:
  sample_rate: 8000
  channels: 1
  chunk_size: 160

logging:
  level: "DEBUG"
  file: "test.log"
```

## Environment Variables

Configuration can be overridden with environment variables:

```bash
export SIP_TRUNK_HOST="sip.example.com"
export SIP_USERNAME="user123"
export SIP_PASSWORD="pass456"
export MQTT_BROKER_HOST="mqtt.example.com"
export MQTT_CLIENT_ID="custom-client-id"
```

## Configuration Validation

The client validates configuration on startup:

- Required fields must be present
- Port numbers must be valid (1-65535)
- Log level must be valid
- YAML syntax must be correct

Invalid configuration will cause startup failure with descriptive error messages.

## Reloading Configuration

Configuration is loaded once at startup. To apply changes:

1. Stop the client: `Ctrl+C` or `kill <pid>`
2. Edit configuration file
3. Restart the client

## Configuration Best Practices

### Security

```yaml
# Use environment variables for secrets
sip:
  password: "${SIP_PASSWORD}"  # Set SIP_PASSWORD env var

mqtt:
  password: "${MQTT_PASSWORD}"  # Set MQTT_PASSWORD env var
```

### Maintainability

```yaml
# Use descriptive names
mqtt:
  client_id: "lobby-phone-001"  # Good
  # client_id: "client1"       # Bad

# Organize topics hierarchically
mqtt:
  topics:
    call_status: "building/floor/room/phone/status"
```

### Performance

```yaml
# Adjust audio buffer for low latency
audio:
  chunk_size: 80  # 10ms at 8kHz (lower = lower latency)

# Reduce logging in production
logging:
  level: "WARNING"
```
