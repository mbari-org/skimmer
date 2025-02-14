from hashlib import md5

from diskcache import Cache
from cachetools import LRUCache
from PIL import Image

from skimmer.config import IMAGE_CACHE_SIZE_MB, ROI_CACHE_SIZE_MB, CACHE_DIR


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


class CachedROI:
    def __init__(self, data: bytes):
        self.data = data
        self.headers = {}

    def get_data(self) -> bytes:
        return self.data


class CacheController:
    def __init__(self):
        # Diskcache for ROIs
        self._roi_cache = Cache(CACHE_DIR, size_limit=ROI_CACHE_SIZE_MB * 1024**2)
        self._roi_cache.expire()  # Ensure expired items are removed

        # In-memory cache for full images
        self._image_cache = LRUCache(
            maxsize=IMAGE_CACHE_SIZE_MB * 1024**2,
            getsizeof=lambda image: len(image.tobytes()),
        )

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
        return self._image_cache.get(key)

    def clear_roi_cache(self):
        """
        Clear the ROI cache.
        """
        self._roi_cache.clear()

    def clear_image_cache(self):
        """
        Clear the image cache.
        """
        self._image_cache.clear()

    def clear(self):
        """
        Clear both the ROI and image caches.
        """
        self.clear_roi_cache()
        self.clear_image_cache()
