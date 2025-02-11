# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the app files to the container
COPY pyproject.toml README.md /app/
COPY src/ /app/src/

# Install the app
RUN pip install .

# Copy the rest of the application code to the container
COPY src/ /app/src/
COPY .env.example /app/.env

# Expose the port the app runs on
EXPOSE 5000

# Set environment variables
ENV CACHE_SIZE=100 \
    CACHE_TTL=300 \
    CACHE_DIR=/tmp/skimmer_cache \
    APP_HOST=0.0.0.0 \
    APP_PORT=5000 \
    APP_DEBUG=false

# Run the application
CMD ["skimmer"]
