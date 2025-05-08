# Build stage
FROM python:3.13-alpine AS builder

WORKDIR /app

# Copy only what's needed for installation
COPY pyproject.toml README.md src /app/

# Install build dependencies and the app, then clean up
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers && \
    pip install --no-cache-dir . && \
    apk del .build-deps

# Runtime stage
FROM python:3.13-alpine

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY env/gunicorn.conf.py /app/
COPY env/.env.example /app/.env

# Set environment variable defaults
ENV IMAGE_CACHE_SIZE_MB=100 \
    ROI_CACHE_SIZE_MB=1000 \
    CACHE_DIR=/tmp/skimmer_cache \
    APP_HOST=0.0.0.0 \
    APP_PORT=5000 \
    APP_WORKERS=1

# Run the application
CMD ["sh", "-c", "exec gunicorn -w $APP_WORKERS -b $APP_HOST:$APP_PORT 'skimmer:create_default_flask_app()'"]

