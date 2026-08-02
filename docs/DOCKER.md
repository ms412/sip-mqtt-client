# Docker Deployment Guide

## Quick Start

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f sip-mqtt-client

# Stop
docker-compose down
```

## Building the Image

### Local Build

```bash
# Build image
docker build -t sip-mqtt-client:latest .

# Build with no cache
docker build --no-cache -t sip-mqtt-client:latest .

# Build for specific platform
docker build --platform linux/amd64 -t sip-mqtt-client:latest .
```

### Multi-Architecture Build

```bash
# Enable buildx
docker buildx create --use

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t sip-mqtt-client:latest --push .
```

## Running the Container

### From GHCR

```bash
# Login to GHCR
docker login ghcr.io -u <username>

# Pull and run
docker run -d \
  --name sip-mqtt-client \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  ghcr.io/<username>/sip-mqtt-client:latest
```

### Basic

```bash
docker run -d \
  --name sip-mqtt-client \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  sip-mqtt-client:latest
```

### With PulseAudio

```bash
docker run -d \
  --name sip-mqtt-client \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
  -v /run/user/1000/pulse/native:/run/user/1000/pulse/native \
  --group-add $(getent group pulseaudio | cut -d: -f3) \
  sip-mqtt-client:latest
```

### With Docker Compose

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d sip-mqtt-client

# Rebuild and start
docker-compose up -d --build
```

## Configuration

### Volume Mounts

| Volume | Purpose |
|--------|---------|
| `./config.yaml:/app/config.yaml:ro` | Configuration file |
| `./logs:/app/logs` | Log files |
| `PULSE_SERVER` | PulseAudio socket |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PULSE_SERVER` | PulseAudio server address |
| `SIP_TRUNK_HOST` | Override SIP trunk host |
| `MQTT_BROKER_HOST` | Override MQTT broker host |

### Example docker-compose.yml

```yaml
version: '3.8'

services:
  sip-mqtt-client:
    build: .
    container_name: sip-mqtt-client
    restart: unless-stopped
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./logs:/app/logs
    environment:
      - PULSE_SERVER=unix:/run/user/1000/pulse/native
    depends_on:
      - mosquitto
    networks:
      - sip-mqtt-network

  mosquitto:
    image: eclipse-mosquitto:2
    container_name: mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto/config:/mosquitto/config:ro
    networks:
      - sip-mqtt-network

networks:
  sip-mqtt-network:
    driver: bridge
```

## Mosquitto Configuration

Create `mosquitto/config/mosquitto.conf`:

```conf
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
```

## CI/CD Integration

### GitHub Actions

The project includes GitHub Actions workflows:

- `.github/workflows/ci.yml` - Main CI pipeline
- `.github/workflows/pr.yml` - PR validation

### Workflow Steps

1. **Test Job**
   - Run unit tests with coverage
   - Enforce 90% coverage threshold
   - Upload coverage report

2. **Build Job** (main branch only)
   - Requires test job success
   - Build Docker image
   - Push to Docker Hub

### Required Secrets

Configure in GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

### Manual Docker Hub Push

```bash
# Login
docker login -u USERNAME -p TOKEN

# Tag
docker tag sip-mqtt-client:latest USERNAME/sip-mqtt-client:latest

# Push
docker push USERNAME/sip-mqtt-client:latest
```

## Troubleshooting

### PulseAudio Issues

```bash
# Check PulseAudio is running
pulseaudio --check

# Allow Docker to access PulseAudio
xhost +local:docker

# Verify socket exists
ls -la /run/user/1000/pulse/native
```

### Network Issues

```bash
# Check container network
docker network inspect sip-mqtt-network

# Test MQTT connectivity
docker exec sip-mqtt-client nc -zv mosquitto 1883

# Test SIP connectivity
docker exec sip-mqtt-client nc -zv sip.trunk.provider.com 5060
```

### Log Analysis

```bash
# View container logs
docker-compose logs -f sip-mqtt-client

# View last 100 lines
docker-compose logs --tail=100 sip-mqtt-client

# Export logs
docker-compose logs sip-mqtt-client > logs.txt
```

## Performance Tuning

### Resource Limits

```yaml
services:
  sip-mqtt-client:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M
```

### Health Check

```yaml
services:
  sip-mqtt-client:
    healthcheck:
      test: ["CMD", "pgrep", "-f", "main.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

## Security Best Practices

### Non-Root User

The Dockerfile runs as non-root user `sipuser` (UID 1000).

### Read-Only Config

```yaml
volumes:
  - ./config.yaml:/app/config.yaml:ro  # Read-only
```

### Network Isolation

```yaml
networks:
  sip-mqtt-network:
    driver: bridge
    internal: false  # Set true for no external access
```

### Secrets Management

```yaml
# Use Docker secrets (Swarm mode)
services:
  sip-mqtt-client:
    secrets:
      - sip_password
      - mqtt_password

secrets:
  sip_password:
    external: true
  mqtt_password:
    external: true
```

## Monitoring

### Container Stats

```bash
docker stats sip-mqtt-client
```

### Health Check

```bash
docker inspect --format='{{.State.Health.Status}}' sip-mqtt-client
```

### Prometheus Metrics (Future)

Export metrics via MQTT or HTTP endpoint for Prometheus scraping.

## Updates

### Manual Update

```bash
# Pull latest image
docker pull USERNAME/sip-mqtt-client:latest

# Recreate container
docker-compose up -d --force-recreate
```

### Watchtower (Automatic)

```yaml
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 300 sip-mqtt-client
```

## Backup and Restore

### Backup Configuration

```bash
tar -czf sip-mqtt-backup.tar.gz \
  config.yaml \
  mosquitto/config/ \
  logs/
```

### Restore Configuration

```bash
tar -xzf sip-mqtt-backup.tar.gz
docker-compose up -d
```
