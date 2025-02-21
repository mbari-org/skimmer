#!/bin/bash

# Source environment variables from .env file if it exists
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Set environment variable defaults
if [ -z "$APP_HOST" ]; then
    export APP_HOST=0.0.0.0
fi
if [ -z "$APP_PORT" ]; then
    export APP_PORT=5000
fi
if [ -z "$APP_WORKERS" ]; then
    export APP_WORKERS=1
fi

# Run the app
uvicorn \
    --host $APP_HOST \
    --port $APP_PORT \
    --workers $APP_WORKERS \
    --factory \
    'skimmer:create_default_fastapi_app'
