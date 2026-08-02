# Contributing to SIP-MQTT Client

Thank you for considering contributing to SIP-MQTT Client! This document provides guidelines and instructions for contributing.

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/yourusername/sip-mqtt-client.git
cd sip-mqtt-client
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Development Dependencies

```bash
pip install -e ".[test]"
```

### 4. Verify Setup

```bash
pytest
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Keep functions focused and under 50 lines when possible
- Use descriptive variable names
- Add docstrings for public APIs

### Example

```python
def process_message(self, message: str, addr: tuple) -> None:
    """Process incoming SIP message.
    
    Args:
        message: Raw SIP message string
        addr: Remote address tuple (ip, port)
    """
    lines = message.split("\r\n")
    if not lines:
        return
```

## Testing

### Writing Tests

- Write tests for all new functionality
- Maintain 90%+ code coverage
- Use descriptive test names: `test_<method>_<scenario>_<expected>`
- Use fixtures for common setup
- Mock external dependencies

### Example Test

```python
def test_handle_invite_callback(self, sip_client, mock_socket):
    """Test that on_incoming_call callback is triggered on INVITE."""
    callback_called = []
    sip_client.on_incoming_call = lambda c: callback_called.append(c)
    message = "INVITE sip:test@sip.example.com SIP/2.0\r\nCall-ID: 123\r\n"
    sip_client._handle_invite(message, ("192.168.1.1", 5060))
    assert len(callback_called) == 1
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov

# Specific test file
pytest tests/test_sip_client.py

# Specific test
pytest tests/test_sip_client.py::TestSIPClient::test_init
```

## Pull Request Process

1. **Create Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code
   - Write tests
   - Update documentation

3. **Run Tests**
   ```bash
   pytest --cov-fail-under=90
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance tasks

### Examples

```
feat: add DTMF detection support
fix: handle connection timeout in MQTT handler
docs: update configuration examples
test: add unit tests for SIP client
refactor: extract audio routing logic
```

## Documentation

### Code Documentation

- Add docstrings to all public classes and methods
- Include Args, Returns, and Raises sections
- Keep docstrings up to date with code changes

### User Documentation

- Update README.md for user-facing changes
- Update configuration examples
- Document new MQTT topics
- Add troubleshooting entries

## Issue Reporting

### Bug Reports

Include:
- Python version
- OS and version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Log output (with DEBUG level)

### Feature Requests

Include:
- Problem description
- Proposed solution
- Use case examples
- Alternative solutions considered

## Architecture Decisions

### SIP Protocol

- UDP transport for SIP messages
- Standard RFC 3261 compliance
- Support for INVITE, BYE, CANCEL, ACK
- DTMF via RFC 2833 (telephone-event)

### MQTT Integration

- QoS 0 for status updates
- QoS 1 for control commands
- JSON payload format
- Topic hierarchy: `sip/<category>/<event>`

### Audio Pipeline

- 8kHz sample rate (telephony standard)
- 16-bit PCM format
- Mono channel
- PulseAudio for system integration

## Code Review Guidelines

### Reviewers Should Check

- [ ] Code follows style guidelines
- [ ] Tests cover new functionality
- [ ] Coverage remains above 90%
- [ ] Documentation is updated
- [ ] No security issues introduced
- [ ] Error handling is adequate
- [ ] Logging is appropriate

### Review Response Time

- We aim to review PRs within 48 hours
- Please be patient and constructive

## Questions?

- Open an issue for questions
- Check existing documentation
- Review closed issues for similar questions

## License

This project is licensed under the Beer-Ware License. See [LICENSE](../LICENSE) for details.

## Thank You!

Your contributions make SIP-MQTT Client better for everyone. We appreciate your time and effort!
