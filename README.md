# Skimmer

## Description
Skimmer is a highly-performant service that fetches an image from a URL, crops it based on provided bounding box coordinates, caches the result using an LRU cache, and returns the cropped image.

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

2. Run the Docker container:
   ```sh
   docker run -p 5000:5000 --env-file .env skimmer
   ```

## Environment Variables
- `CACHE_SIZE`: The maximum number of items to store in the LRU cache (default: 100).
- `CACHE_TTL`: The time-to-live for cache items in seconds (default: 300).
- `CACHE_DIR`: The directory to store the filesystem cache (default: `/tmp/skimmer_cache`).
- `APP_HOST`: The host address for the Flask application (default: `0.0.0.0`).
- `APP_PORT`: The port for the Flask application (default: 5000).
- `APP_DEBUG`: Enable or disable debug mode for the Flask application (default: `false`).

## Running Tests

```sh
pytest
```

## Custom Headers
The service returns custom headers to indicate the cache status of the image:
- `X-Cache`: Indicates whether the image was a cache hit or miss. Possible values are `HIT` or `MISS`.
- `X-Cache-Source`: Indicates the source of the cache hit. Possible values are `Memory` or `Filesystem` (or `None` in the case of `X-Cache: MISS`).
