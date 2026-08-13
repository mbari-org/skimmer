from os import cpu_count, getenv
from pathlib import Path

# Configure image and ROI cache sizes
IMAGE_CACHE_SIZE_MB = int(getenv("IMAGE_CACHE_SIZE_MB", 100))
ROI_CACHE_SIZE_MB = int(getenv("ROI_CACHE_SIZE_MB", 100))

# diskcache's "least-recently-used" policy writes to SQLite (bumping
# access_time) on every read, not just writes -- under concurrent load this
# serializes on SQLite's single-writer lock and dominates tail latency.
# "least-recently-stored" needs no write on read (orders eviction by
# store_time instead), trading LRU precision for read throughput -- a good
# trade once the cache is sized to hold the working set (ROI_CACHE_SIZE_MB)
# so eviction is rare either way.
ROI_CACHE_EVICTION_POLICY = getenv("ROI_CACHE_EVICTION_POLICY", "least-recently-stored")

# Configure filesystem cache directory
CACHE_DIR = Path(getenv("CACHE_DIR", "/tmp/skimmer_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Configure Beholder client parameters
BEHOLDER_URL = getenv("BEHOLDER_URL")
BEHOLDER_API_KEY = getenv("BEHOLDER_API_KEY")

# Bounded concurrency gate for crop generation (see skimmer/backpressure.py),
# mirroring Beholder's beholder.capture.{threads,queuesize,maxwait}.
# 0 = auto (a small multiple of the CPU count).
CROP_POOL_SLOTS = int(getenv("CROP_POOL_SLOTS", 0)) or max(2, (cpu_count() or 4) // 2)
CROP_POOL_QUEUE_SIZE = int(getenv("CROP_POOL_QUEUE_SIZE", 0)) or CROP_POOL_SLOTS * 8
CROP_POOL_MAX_WAIT_SECONDS = float(getenv("CROP_POOL_MAX_WAIT_SECONDS", 15.0))
