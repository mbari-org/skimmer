from os import getenv
from pathlib import Path


# Configure Flask app parameters
APP_NAME = "skimmer"

# Configure image and ROI cache sizes
IMAGE_CACHE_SIZE_MB = int(getenv("IMAGE_CACHE_SIZE_MB", 100))
ROI_CACHE_SIZE_MB = int(getenv("ROI_CACHE_SIZE_MB", 100))

# Configure filesystem cache directory
CACHE_DIR = Path(getenv("CACHE_DIR", "/tmp/skimmer_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Configure Beholder client parameters
BEHOLDER_URL = getenv("BEHOLDER_URL")
BEHOLDER_API_KEY = getenv("BEHOLDER_API_KEY")