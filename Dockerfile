# syntax=docker/dockerfile:1.4

# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install dependencies via pip (simpler for Docker)
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir click werkzeug flask markdown2 emoji frozen-flask

# Runtime stage
FROM python:3.12-slim as runtime

# Install curl for healthcheck (optional)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

WORKDIR /app

# Copy dependencies from builder to ensure they're available in the runtime image
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY . .

# Create user with UID/GID matching host for file permissions
RUN groupadd -g 1000 app && useradd -u 1000 -g app -m app

# Switch to non-root user
USER app

# Expose default port
EXPOSE 5000

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Default command - can be overridden
CMD ["python", "app.py", "--help"]
