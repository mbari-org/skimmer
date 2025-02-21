# Skimmer

Skimmer is a service that fetches an image from a URL, crops it based on provided bounding box coordinates, caches the result in memory & on the filesystem, and returns the cropped image.

Skimmer also integrates with [Beholder](https://github.com/mbari-org/beholder) to fetch frames from videos.

[![license](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/downloads/)
[![.github/workflows/ci.yaml](https://github.com/mbari-org/skimmer/actions/workflows/ci.yaml/badge.svg)](https://github.com/mbari-org/skimmer/actions/workflows/ci.yaml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)

Author: Kevin Barnard ([kbarnard@mbari.org](mailto:kbarnard@mbari.org))

## :hammer: Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/mbari-org/skimmer.git
   cd skimmer
   ```

2. Install the package:
   ```sh
   pip install .
   ```

3. Set up environment variables:
   ```sh
   cp .env.example .env
   ```

## :rocket: Usage

Run scripts for Flask + gunicorn (WSGI) and FastAPI + uvicorn (ASGI) are provided to start the service. Set the appropriate environment variables in `.env`, then run:
```sh
./run_flask.sh
```
or
```sh
./run_fastapi.sh
```

### API

#### Crop

The main endpoint of the service is `/crop`, which takes the following query parameters:
- `url`: The URL of the image or video to crop.
- `left`: The left coordinate of the bounding box.
- `top`: The top coordinate of the bounding box.
- `right`: The right coordinate of the bounding box.
- `bottom`: The bottom coordinate of the bounding box.
- `ms`: The timestamp in milliseconds for videos.

The response will be a PNG image representing the cropped region of interest.

- Image:
   ```sh
   curl http://localhost:5000/crop?url=http://example.com/image.jpg&left=0&top=0&right=100&bottom=100
   # image bytes
   ```

- Video (@ 1000 ms):
   ```sh
   curl http://localhost:5000/crop?url=http://example.com/video.mp4&left=0&top=0&right=100&bottom=100&ms=1000
   # image bytes
   ```

#### Health Check

The service also provides a health check endpoint at `/health` that returns a 200 status code if the service is running and a JSON response with some process info. For example:
```sh
curl http://localhost:5000/health
# {"jdkVersion": "Python 3.12.9 (main, Feb  5 2025, 08:49:00) [GCC 11.4.0]", "availableProcessors": 20, "freeMemory": 28491902976, "maxMemory": 33434419200, "totalMemory": 33434419200, "application": "skimmer", "version": "0.1.0", "description": "ROI Service"}
```

## :whale: Docker

Skimmer is available on Docker Hub as [`mbari/skimmer`](https://hub.docker.com/repository/docker/mbari/skimmer). To run the service in a Docker container:

```sh
docker run \
   -p 5000:5000 \
   --env-file .env \
   -v /path/to/local/cache:/tmp/skimmer_cache \
   mbari/skimmer
```

Replace `/path/to/local/cache` with the path to a directory on your host machine where you want to store the cached images persistently.

### Compose

An example [`compose.yaml`](docker/compose.yaml) is provided. To run Skimmer with Docker Compose, first edit the compose file to set the environment variables as desired, then run:
```sh
docker compose -f docker/compose.yaml up
```

## :gear: Environment Variables

### App
- `APP_HOST`: The host address for the Flask application (default: `0.0.0.0`).
- `APP_PORT`: The port for the Flask application (default: 5000).
- `APP_WORKERS`: The number of worker processes for handling requests (default: 1).

### Cache
- `IMAGE_CACHE_SIZE_MB`: The maximum size of the in-memory cache for full images in megabytes (default: 100). Note that this is per-worker, so the total memory usage will be approximately `APP_WORKERS * IMAGE_CACHE_SIZE_MB`.
- `CACHE_DIR`: The directory to store the filesystem cache (default: `/tmp/skimmer_cache`).
- `ROI_CACHE_SIZE_MB`: The maximum size of the filesystem cache for ROIs in megabytes (default: 100).

### Beholder
- `BEHOLDER_URL`: The URL of the Beholder service to use for fetching images. If unspecified, the service will still work for static images, but it will not be able to fetch frames from video using Beholder.
- `BEHOLDER_API_KEY`: The API key to use for authenticating with the Beholder service.

## Running Tests

Pytest is used for testing. To run the tests, simply run:
```sh
pytest
```

Note that this will use the environment from `.env.test` for testing.

## Custom Headers
The service returns custom headers to indicate the cache status of the image:
- `X-Cache`: Indicates whether the image was a cache hit or miss. Possible values are `HIT` or `MISS`.

---

Copyright &copy; 2025 [Monterey Bay Aquarium Research Institute](https://mbari.org/)