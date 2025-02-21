# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the app files to the container
COPY pyproject.toml README.md env/gunicorn.conf.py /app/
COPY src/ /app/src/

# Install the app
RUN pip install .

# Copy the rest of the application code to the container
COPY src/ /app/src/
COPY env/.env.example /app/.env

# Expose the port the app runs on
EXPOSE 5000

# Set environment variable defaults
ENV IMAGE_CACHE_SIZE_MB=100
ENV ROI_CACHE_SIZE_MB=1000
ENV CACHE_DIR=/tmp/skimmer_cache
ENV APP_HOST=0.0.0.0
ENV APP_PORT=5000
ENV APP_WORKERS=1

# Run the application
CMD ["sh", "-c", "exec gunicorn -w $APP_WORKERS -b $APP_HOST:$APP_PORT 'skimmer:create_default_flask_app()'"] 
 
