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
gunicorn \
    --bind $APP_HOST:$APP_PORT \
    --workers $APP_WORKERS \
    --config env/gunicorn.conf.py \
    'skimmer:create_default_flask_app()'
