from os import getenv
from pathlib import Path

# Configure image and ROI cache sizes
IMAGE_CACHE_SIZE_MB = int(getenv("IMAGE_CACHE_SIZE_MB", 100))
ROI_CACHE_SIZE_MB = int(getenv("ROI_CACHE_SIZE_MB", 100))

# Configure filesystem cache directory
CACHE_DIR = Path(getenv("CACHE_DIR", "/tmp/skimmer_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Configure Flask app parameters
APP_HOST = getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(getenv("APP_PORT", 5000))
APP_DEBUG = getenv("APP_DEBUG", "false").lower() == "true"
