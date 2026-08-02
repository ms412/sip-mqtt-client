# GitHub Container Registry (GHCR) Guide

## Overview

This project uses GitHub Container Registry (GHCR) for Docker image hosting. Images are automatically built and pushed on every push to the main branch.

## Image URL

```
ghcr.io/<username>/sip-mqtt-client:latest
```

Replace `<username>` with your GitHub username or organization name.

## Available Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest build from main branch |
| `sha-<hash>` | Specific commit SHA |
| `v1.0.0` | Semantic version (on release) |
| `v1.0` | Minor version (on release) |
| `v1` | Major version (on release) |
| `2024-01-15` | Date-based tag |

## Authentication

### Pull Images

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

# Pull image
docker pull ghcr.io/<username>/sip-mqtt-client:latest
```

### GitHub Actions (Automatic)

The CI workflow uses `GITHUB_TOKEN` automatically for authentication.

## CI/CD Workflows

### Main CI Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` branch
- Pull requests to `main` branch

**Jobs:**

1. **test** - Runs on all pushes/PRs
   - Python 3.11
   - Installs dependencies
   - Runs tests with 90% coverage requirement
   - Uploads coverage report

2. **build** - Runs only on main branch push (after tests pass)
   - Builds Docker image
   - Pushes to GHCR
   - Uses build cache for faster builds

### Release Pipeline (`.github/workflows/release.yml`)

**Triggers:**
- GitHub release published

**Features:**
- Multi-architecture build (amd64, arm64)
- Semantic versioning tags
- Pushes to GHCR

## Usage Examples

### Docker CLI

```bash
# Login
docker login ghcr.io -u <username>

# Pull
docker pull ghcr.io/<username>/sip-mqtt-client:latest

# Run
docker run -d \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  ghcr.io/<username>/sip-mqtt-client:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  sip-mqtt-client:
    image: ghcr.io/${{ github.repository_owner }}/sip-mqtt-client:latest
    container_name: sip-mqtt-client
    restart: unless-stopped
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    environment:
      - PULSE_SERVER=unix:/run/user/1000/pulse/native
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sip-mqtt-client
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sip-mqtt-client
  template:
    metadata:
      labels:
        app: sip-mqtt-client
    spec:
      containers:
      - name: sip-mqtt-client
        image: ghcr.io/<username>/sip-mqtt-client:latest
        imagePullPolicy: Always
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: sip-mqtt-config
      imagePullSecrets:
      - name: ghcr-secret
```

## Package Settings

### Configure Package Visibility

1. Go to repository **Settings**
2. Navigate to **Packages**
3. Select `sip-mqtt-client`
4. Change visibility:
   - **Public**: Anyone can pull
   - **Private**: Only authenticated users with access

### Package Versioning

Each push creates a new package version. Old versions can be deleted in:
**Settings** → **Packages** → Select version → **Delete**

## Local Development

### Build and Test Locally

```bash
# Build
docker build -t ghcr.io/<username>/sip-mqtt-client:test .

# Test
docker run --rm ghcr.io/<username>/sip-mqtt-client:test python -m pytest

# Tag for GHCR
docker tag ghcr.io/<username>/sip-mqtt-client:test ghcr.io/<username>/sip-mqtt-client:latest
```

### Push to GHCR Manually

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

# Push
docker push ghcr.io/<username>/sip-mqtt-client:latest
```

## GitHub Actions Secrets

No additional secrets required for GHCR! The workflow uses:

- `${{ github.actor }}` - Your GitHub username
- `${{ secrets.GITHUB_TOKEN }}` - Auto-generated token

For private repositories, ensure `GITHUB_TOKEN` has `packages: write` permission.

## Troubleshooting

### Pull Permission Denied

```bash
# Ensure you're logged in
docker login ghcr.io -u <username>

# Check package visibility in GitHub settings
```

### Push Permission Denied

- Verify you have write access to the repository
- Check `GITHUB_TOKEN` permissions in workflow
- For releases, ensure release was published (not draft)

### Build Cache Issues

```bash
# Disable cache in workflow
cache-from: ""
cache-to: ""

# Or clear cache in GHCR settings
```

## Migration from Docker Hub

### Update Image References

```yaml
# Before (Docker Hub)
image: username/sip-mqtt-client:latest

# After (GHCR)
image: ghcr.io/username/sip-mqtt-client:latest
```

### Update CI/CD

Remove Docker Hub secrets and login:

```yaml
# Remove
- name: Login to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}

# Replace with
- name: Login to GitHub Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

## Best Practices

### Image Cleanup

Periodically delete old package versions:
- Keep `latest` and recent versions
- Delete old `sha-*` tags
- Use GHCR API for automation

### Security

- Use minimal base image (slim/alpine)
- Run as non-root user
- Scan images for vulnerabilities
- Keep dependencies updated

### Performance

- Use build cache effectively
- Multi-stage builds
- Multi-architecture for ARM support
- Layer optimization

## API Access

### List Packages

```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/orgs/<org>/packages/container/sip-mqtt-client/versions
```

### Delete Package Version

```bash
curl -X DELETE \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/orgs/<org>/packages/container/sip-mqtt-client/versions/<version_id>
```

## Resources

- [GHCR Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Metadata Action](https://github.com/docker/metadata-action)
- [Docker Buildx Action](https://github.com/docker/build-push-action)
