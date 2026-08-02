# SIP-MQTT Client Architecture

## Overview

SIP-MQTT Client is a bridge between SIP telephony and IoT/MQTT ecosystems. It enables remote call control and monitoring through MQTT while maintaining full SIP protocol compliance.

## System Components

### 1. SIP Client (`sip_client/`)

Handles all SIP protocol communication.

#### Responsibilities
- SIP message parsing and generation
- Call state management
- RTP/DTMF handling
- Registration with SIP trunk

#### Key Classes

**SIPClient**
- Main SIP protocol handler
- Manages UDP socket for SIP messages
- Processes incoming INVITE, BYE, CANCEL
- Triggers callbacks for call events

**Call**
- Represents a single call session
- Handles call answering and termination
- Manages RTP streams
- Sends/receives DTMF tones

#### Message Flow

```
Incoming Call:
SIP Trunk ─INVITE─> SIP Client ─100 Trying─> SIP Trunk
                         │
                         └─180 Ringing─> SIP Trunk
                         │
                         └─Callback: on_incoming_call()
                         │
MQTT Control ─answer─> SIP Client ─200 OK─> SIP Trunk
                         │
                         └─RTP stream established

Call Termination:
Remote Party ─BYE─> SIP Client
                      │
                      └─Callback: on_call_ended("remote_hangup")
                      │
                      └─MQTT Publish: {"status": "ended"}
```

### 2. MQTT Handler (`mqtt_handler/`)

Manages MQTT communication for control and monitoring.

#### Responsibilities
- MQTT broker connection management
- Topic subscription
- Message publishing
- Automatic reconnection

#### Topics

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `sip/call/status` | Publish | Call state changes |
| `sip/call/control` | Subscribe | Call control commands |
| `sip/dtmf` | Publish | DTMF events |
| `sip/audio/control` | Subscribe | Audio stream control |

#### Message Formats

**Call Status**
```json
{
  "status": "incoming",
  "caller_id": "123456789",
  "call_id": "uuid-123",
  "timestamp": 1699000000.0
}
```

**Call Control**
```json
{
  "action": "answer"
}
```

**DTMF Event**
```json
{
  "digit": "5",
  "duration": 100,
  "timestamp": 1699000000.0
}
```

### 3. Audio Handler (`audio/`)

Manages audio I/O through PulseAudio.

#### Responsibilities
- Audio device management
- PCM audio streaming
- Sample rate conversion
- Buffer management

#### Audio Pipeline

```
RTP Packets ─> Depacketize ─> PCM Buffer ─> PulseAudio Sink
PulseAudio Source ─> PCM Buffer ─> Packetize ─> RTP Packets
```

#### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sample_rate` | 8000 Hz | Telephony standard |
| `channels` | 1 | Mono audio |
| `chunk_size` | 160 | 20ms at 8kHz |
| `sink_name` | sip_output | PulseAudio output |
| `source_name` | sip_input | PulseAudio input |

## Data Flow

### Incoming Call Flow

```
1. SIP INVITE received
   └─> SIP Client processes INVITE
   └─> Call object created
   └─> 100 Trying sent
   └─> 180 Ringing sent

2. MQTT Status Published
   └─> {"status": "incoming", "caller_id": "..."}

3. MQTT Control: answer
   └─> Call.answer() called
   └─> 200 OK sent
   └─> RTP streams started
   └─> Audio handler connected

4. Call Active
   └─> Audio flows bidirectionally
   └─> DTMF detection active

5. Call Ended
   └─> BYE received/sent
   └─> RTP streams stopped
   └─> MQTT status: "ended"
```

### DTMF Detection Flow

```
1. RTP packet with telephone-event
   └─> SIP Client parses NOTIFY
   └─> DTMF digit extracted

2. MQTT Publish
   └─> {"digit": "5", "duration": 100}

3. Control Server receives
   └─> Process DTMF command
   └─> Take appropriate action
```

## Thread Model

```
Main Thread
├─ Signal handling (SIGINT, SIGTERM)
└─ Event loop (signal.pause)

SIP Receive Thread
└─ UDP socket polling
   └─ Message processing
      └─ Callback invocation

MQTT Client Thread
├─ Network loop (paho-mqtt)
├─ Message dispatch
└─ Reconnection handling

Audio Input Thread
└─ PulseAudio source read
   └─ RTP packetization
      └─ Network send

Audio Output Thread
├─ RTP packet receive
├─ Depacketization
└─ PulseAudio sink write
```

## Error Handling

### SIP Layer

| Error | Handling |
|-------|----------|
| Network timeout | Retry with exponential backoff |
| Invalid message | Log and discard |
| Registration failure | Log error, continue without registration |
| Call setup failure | Send appropriate SIP response |

### MQTT Layer

| Error | Handling |
|-------|----------|
| Connection lost | Automatic reconnection |
| Publish failure | Log error, continue |
| Invalid payload | Log error, discard message |

### Audio Layer

| Error | Handling |
|-------|----------|
| Device not found | Log error, use default device |
| Buffer underrun | Log warning, continue |
| Format unsupported | Log error, fail gracefully |

## Configuration Loading

```
config.yaml
    │
    └─> yaml.safe_load()
        │
        └─> SIPMQTTClient.__init__()
            │
            ├─> SIPClient(**config["sip"])
            ├─> MQTTHandler(**config["mqtt"])
            └─> PulseAudioHandler(**config["audio"])
```

## Security Considerations

### Network Security

- SIP: UDP (consider TLS for production)
- MQTT: Use TLS (mqtts://) in production
- Firewall: Restrict to known IP ranges

### Authentication

- SIP: Digest authentication supported
- MQTT: Username/password authentication
- Audio: Local-only by default

### Authorization

- MQTT ACLs for topic access
- SIP trunk provider restrictions
- Local firewall rules

## Performance Characteristics

### Resource Usage

| Component | Memory | CPU |
|-----------|--------|-----|
| SIP Client | ~5 MB | <1% |
| MQTT Handler | ~2 MB | <1% |
| Audio Handler | ~10 MB | 2-5% |
| **Total** | **~17 MB** | **<10%** |

### Latency

| Operation | Target | Typical |
|-----------|--------|---------|
| Call answer | <500ms | ~200ms |
| DTMF detection | <100ms | ~50ms |
| MQTT publish | <100ms | ~20ms |
| Audio latency | <150ms | ~50ms |

## Scalability

### Single Instance

- Handles 1 concurrent call
- Suitable for single-line applications
- Low resource footprint

### Multi-Instance

- Multiple clients with unique client_id
- Load balancing via MQTT topics
- Consider session affinity for calls

## Monitoring and Observability

### Logs

```
INFO: SIP client started on 192.168.1.100:5060
INFO: MQTT client started, connected to localhost:1883
INFO: Incoming call from 123456789
INFO: Call answered
INFO: DTMF received: 5
INFO: Call ended: remote_hangup
```

### Metrics (Future)

- Calls answered/missed
- Average call duration
- DTMF count
- MQTT message rate
- Audio buffer underruns

## Future Enhancements

### Planned
- [ ] Multiple concurrent calls
- [ ] SIP over TCP/TLS
- [ ] MQTT over TLS
- [ ] Call recording
- [ ] Voicemail support
- [ ] WebRTC gateway
- [ ] Prometheus metrics
- [ ] Grafana dashboards

### Considered
- [ ] Video call support
- [ ] Conference calling
- [ ] Call transfer (REFER)
- [ ] Presence (RPID)

## Dependencies

### Runtime
- Python 3.8+
- paho-mqtt >= 1.6.1
- pyaudio >= 0.2.11
- pyyaml >= 5.4

### Development
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- pytest-mock >= 3.10.0

## Standards Compliance

### SIP
- RFC 3261: SIP: Session Initiation Protocol
- RFC 3264: SDP Offer/Answer
- RFC 2833: DTMF in RTP

### MQTT
- MQTT 3.1.1 (ISO/IEC 20922)
- OASIS MQTT Specification

### Audio
- G.711 μ-law (PCMU)
- G.711 A-law (PCMA)
- RFC 4733: DTMF in RTP
