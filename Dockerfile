FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[test]"

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 sipuser && chown -R sipuser:sipuser /app
USER sipuser

# Default command
CMD ["python", "main.py"]
