#!/usr/bin/env bash

# Set the script's directory as the working directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

# Get the APP_VERSION from skimmer.constants
APP_VERSION=$(python -c "from skimmer.constants import APP_VERSION; print(APP_VERSION)")

# Build and push the Docker image for linux/amd64 and linux/arm64
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t mbari/skimmer:$APP_VERSION \
    -t mbari/skimmer:latest \
    -f Dockerfile \
    --push \
    ..
