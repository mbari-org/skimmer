from hashlib import md5
from threading import Lock

from diskcache import Cache
from cachetools import LRUCache
from PIL import Image

from skimmer.config import (
    CACHE_DIR,
    IMAGE_CACHE_SIZE_MB,
    ROI_CACHE_EVICTION_POLICY,
    ROI_CACHE_SIZE_MB,
    THUMBNAIL_CACHE_DIR,
    THUMBNAIL_CACHE_SIZE_MB,
)


def generate_roi_cache_key(
    url: str, left: int, top: int, right: int, bottom: int, ms: int = 0
) -> str:
    """
    Generate an ROI cache key based on URL and crop parameters.

    Args:
        url (str): The URL of the image or video.
        left (int): The left coordinate of the crop box.
        top (int): The top coordinate of the crop box.
        right (int): The right coordinate of the crop box.
        bottom (int): The bottom coordinate of the crop box.
        ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

    Returns:
        str: The generated ROI cache key.
    """
    key = f"{url}_{ms}_{left}_{top}_{right}_{bottom}"
    return md5(key.encode()).hexdigest()


def generate_thumbnail_cache_key(
    url: str, max_edge: int, quality: int, ms: int = 0
) -> str:
    """
    Generate a thumbnail cache key based on URL and rendering parameters.

    Keyed on the resolved pixel size and quality (not the preset name) so a
    config change produces new thumbnails instead of serving stale ones.

    Args:
        url (str): The URL of the image or video.
        max_edge (int): The longest edge of the thumbnail in pixels.
        quality (int): The JPEG quality.
        ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

    Returns:
        str: The generated thumbnail cache key.
    """
    key = f"thumbnail_{url}_{ms}_{max_edge}_{quality}"
    return md5(key.encode()).hexdigest()


def generate_image_cache_key(url: str, ms: int = 0) -> str:
    """
    Generate an image cache key based on URL (and timestamp for videos).

    Args:
        url (str): The URL of the image or video.
        ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

    Returns:
        str: The generated image cache key.
    """
    return (url, ms)


class CachedImage:
    # Class-level default so entries pickled before media_type existed still load
    media_type = "image/png"

    def __init__(self, data: bytes, media_type: str = "image/png"):
        self.data = data
        self.media_type = media_type
        self.headers = {}

    def get_data(self) -> bytes:
        return self.data


# Alias kept so existing on-disk pickles (stored as CachedROI) still unpickle
CachedROI = CachedImage


class CacheController:
    def __init__(self):
        # Diskcache for ROIs
        self._roi_cache = Cache(
            CACHE_DIR,
            size_limit=ROI_CACHE_SIZE_MB * 1024**2,
            eviction_policy=ROI_CACHE_EVICTION_POLICY,
        )
        self._roi_cache.expire()  # Ensure expired items are removed

        # Diskcache for thumbnails
        self._thumbnail_cache = Cache(
            THUMBNAIL_CACHE_DIR,
            size_limit=THUMBNAIL_CACHE_SIZE_MB * 1024**2,
            eviction_policy=ROI_CACHE_EVICTION_POLICY,
        )
        self._thumbnail_cache.expire()

        # In-memory cache for full images. cachetools.LRUCache is not
        # thread-safe, so access is guarded by _image_cache_lock below.
        self._image_cache = LRUCache(
            maxsize=IMAGE_CACHE_SIZE_MB * 1024**2,
            getsizeof=lambda image: len(image.tobytes()),
        )
        self._image_cache_lock = Lock()

    def set_roi(
        self,
        roi: CachedROI,
        url: str,
        left: int,
        top: int,
        right: int,
        bottom: int,
        ms: int = 0,
    ):
        """
        Set an ROI in the cache.

        Args:
            roi (CachedROI): The cached ROI.
            url (str): The URL of the image or video.
            left (int): The left coordinate of the crop box.
            top (int): The top coordinate of the crop box.
            right (int): The right coordinate of the crop box.
            bottom (int): The bottom coordinate of the crop box.
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.
        """
        key = generate_roi_cache_key(url, left, top, right, bottom, ms=ms)
        self._roi_cache.set(key, roi)

    def set_image(self, image: Image.Image, url: str, ms: int = 0):
        """
        Set an image in the cache.

        Args:
            image (Image.Image): The image to cache.
            url (str): The URL of the image or video.
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.
        """
        key = generate_image_cache_key(url, ms=ms)
        with self._image_cache_lock:
            self._image_cache[key] = image

    def get_roi(
        self, url: str, left: int, top: int, right: int, bottom: int, ms: int = 0
    ) -> CachedROI | None:
        """
        Get an ROI from the cache.

        Args:
            url (str): The URL of the image or video.
            left (int): The left coordinate of the crop box.
            top (int): The top coordinate of the crop box.
            right (int): The right coordinate of the crop box.
            bottom (int): The bottom coordinate of the crop box.
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

        Returns:
            CachedROI | None: The cached ROI or None if not found.
        """
        key = generate_roi_cache_key(url, left, top, right, bottom, ms=ms)
        return self._roi_cache.get(key)

    def get_image(self, url: str, ms: int = 0) -> Image.Image | None:
        """
        Get an image from the cache.

        Args:
            url (str): The URL of the image or video.
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

        Returns:
            Image.Image | None: The cached image or None if not found.
        """
        key = generate_image_cache_key(url, ms=ms)
        with self._image_cache_lock:
            return self._image_cache.get(key)

    def set_thumbnail(
        self, thumbnail: CachedImage, url: str, max_edge: int, quality: int, ms: int = 0
    ):
        """
        Set a thumbnail in the cache.

        Args:
            thumbnail (CachedImage): The cached thumbnail.
            url (str): The URL of the image or video.
            max_edge (int): The longest edge of the thumbnail in pixels.
            quality (int): The JPEG quality.
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.
        """
        key = generate_thumbnail_cache_key(url, max_edge, quality, ms=ms)
        self._thumbnail_cache.set(key, thumbnail)

    def get_thumbnail(
        self, url: str, max_edge: int, quality: int, ms: int = 0
    ) -> CachedImage | None:
        """
        Get a thumbnail from the cache.

        Args:
            url (str): The URL of the image or video.
            max_edge (int): The longest edge of the thumbnail in pixels.
            quality (int): The JPEG quality.
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

        Returns:
            CachedImage | None: The cached thumbnail or None if not found.
        """
        key = generate_thumbnail_cache_key(url, max_edge, quality, ms=ms)
        return self._thumbnail_cache.get(key)

    def clear_roi_cache(self):
        """
        Clear the ROI cache.
        """
        self._roi_cache.clear()

    def clear_thumbnail_cache(self):
        """
        Clear the thumbnail cache.
        """
        self._thumbnail_cache.clear()

    def clear_image_cache(self):
        """
        Clear the image cache.
        """
        with self._image_cache_lock:
            self._image_cache.clear()

    def clear(self):
        """
        Clear the ROI, thumbnail, and image caches.
        """
        self.clear_roi_cache()
        self.clear_thumbnail_cache()
        self.clear_image_cache()
