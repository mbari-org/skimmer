#!/usr/bin/env bash

# Set the script's directory as the working directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

# Get the APP_VERSION from skimmer.constants
APP_VERSION=$(python -c "from skimmer.constants import APP_VERSION; print(APP_VERSION)")

# Push the APP_VERSION and latest Docker images to Docker Hub
docker push mbari/skimmer:$APP_VERSION
docker push mbari/skimmer:latest