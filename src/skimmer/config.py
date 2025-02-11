from os import getenv
from pathlib import Path

# Configure cache size (number of items) and TTL (time to live in seconds)
CACHE_SIZE = int(getenv("CACHE_SIZE", 100))
CACHE_TTL = int(getenv("CACHE_TTL", 300))

# Configure filesystem cache directory
CACHE_DIR = Path(getenv("CACHE_DIR", "/tmp/skimmer_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Configure Flask app parameters
APP_HOST = getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(getenv("APP_PORT", 5000))
APP_DEBUG = getenv("APP_DEBUG", "false").lower() == "true"
