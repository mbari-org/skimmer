# Skimmer

Skimmer is a service that fetches an image from a URL, crops it based on provided bounding box coordinates, caches the result in memory & on the filesystem, and returns the cropped image.

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
1. Run the service:
   ```sh
   skimmer
   ```

2. Access the service by making a GET request to:
   ```
   http://localhost:5000/crop?url=<image_url>&left=<left>&top=<top>&right=<right>&bottom=<bottom>
   ```

## :whale: Docker
1. Build the Docker image:
   ```sh
   docker build -t skimmer .
   ```

2. Run the Docker container with a persistent volume for the image crops:
   ```sh
   docker run -p 5000:5000 --env-file .env -v /path/to/local/cache:/tmp/skimmer_cache skimmer
   ```

   Replace `/path/to/local/cache` with the path to a directory on your host machine where you want to store the cached images persistently.

### Compose

An example `compose.yaml` is provided. To run the service with Docker Compose, first edit this file to set the environment variables as desired. Then run:
```sh
docker compose up
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