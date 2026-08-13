import httpx
from io import BytesIO
from beholder_client import BeholderClient
from PIL import Image

from skimmer.backpressure import AsyncBoundedGate, BoundedGate
from skimmer.cache import CacheController, CachedROI, generate_roi_cache_key
from skimmer.config import (
    BEHOLDER_API_KEY,
    BEHOLDER_URL,
    CROP_POOL_MAX_WAIT_SECONDS,
    CROP_POOL_QUEUE_SIZE,
    CROP_POOL_SLOTS,
)
from skimmer.exceptions import BeholderNotConfiguredError, InvalidURLError
from skimmer.utils import is_url_video, is_valid_url, validate_crop_parameters


HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class Skimmer:
    def __init__(self):
        self._cache = CacheController()
        self._beholder_client = None
        if BEHOLDER_URL is not None and BEHOLDER_API_KEY is not None:
            self._beholder_client = BeholderClient(BEHOLDER_URL, BEHOLDER_API_KEY)

        # Persistent client for connection pooling/keep-alive across requests
        self._http_client = httpx.Client(
            follow_redirects=True, verify=False, timeout=HTTP_TIMEOUT
        )

        # Bounds concurrent crop generation the same way Beholder bounds
        # concurrent ffmpeg captures, so overload sheds load (503) instead of
        # degrading into unbounded tail latency. Only one of these is ever
        # exercised in a given process (Flask uses the sync gate, FastAPI the
        # async one), so having both instantiated is harmless.
        self._crop_gate = BoundedGate(
            CROP_POOL_SLOTS, CROP_POOL_QUEUE_SIZE, CROP_POOL_MAX_WAIT_SECONDS
        )
        self._crop_gate_async = AsyncBoundedGate(
            CROP_POOL_SLOTS, CROP_POOL_QUEUE_SIZE, CROP_POOL_MAX_WAIT_SECONDS
        )

    def fetch_image(self, url: str) -> Image.Image:
        """
        Fetch image from the given URL.

        Args:
            url (str): The URL of the image.

        Returns:
            Image.Image: The fetched image.

        Raises:
            InvalidURLError: If the URL is invalid.
        """
        if not is_valid_url(url):
            raise InvalidURLError(f"Invalid URL: {url}")

        # Check for a cache hit
        image = self._cache.get_image(url)
        if image is not None:
            return image

        # Fetch the image
        response = self._http_client.get(url)
        response.raise_for_status()

        # Convert and cache
        image_bytes = response.content
        with BytesIO(image_bytes) as img_buffer:
            image = Image.open(img_buffer)
            image.load()
            self._cache.set_image(image, url)
            return image

    def fetch_video_frame(self, url: str, ms: int) -> Image.Image:
        """
        Fetch a video frame using Beholder.

        Args:
            url (str): The URL of the video.
            ms (int): The timestamp into the video in milliseconds.

        Returns:
            Image.Image: The fetched video frame.

        Raises:
            InvalidURLError: If the URL is invalid.
            BeholderNotConfiguredError: If Beholder client is not configured.
        """
        if not is_valid_url(url):
            raise InvalidURLError(f"Invalid URL: {url}")

        # Check for Beholder configuration
        if self._beholder_client is None:
            raise BeholderNotConfiguredError(
                "Beholder client is not configured. Set BEHOLDER_URL and BEHOLDER_API_KEY."
            )

        # Check for a cache hit
        image = self._cache.get_image(url, ms=ms)
        if image is not None:
            return image

        # Fetch the frame and convert
        image = self._beholder_client.capture(url, ms)

        # Cache
        self._cache.set_image(image, url, ms=ms)

        return image

    def generate_crop(
        self, url: str, left: int, top: int, right: int, bottom: int, ms: int = 0
    ) -> CachedROI:
        """
        Generate a crop from the given URL based on the provided coordinates.

        Args:
            url (str): The URL of the image or video.
            left (int): The left coordinate of the crop box.
            top (int): The top coordinate of the crop box.
            right (int): The right coordinate of the crop box.
            bottom (int): The bottom coordinate of the crop box.
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

        Returns:
            CachedROI: The cropped image byte array with custom headers.

        Raises:
            InvalidURLError: If the URL is invalid.
            InvalidCropParametersError: If the crop coordinates or timestamp are invalid.
            skimmer.backpressure.Saturated: If the crop pool has no room left.
            skimmer.backpressure.StaleWork: If the request waited too long for a slot.
        """
        if not is_valid_url(url):
            raise InvalidURLError(f"Invalid URL: {url}")
        validate_crop_parameters(left, top, right, bottom, ms)

        # Check for a cache hit
        roi = self._cache.get_roi(url, left, top, right, bottom, ms=ms)
        if roi is not None:
            roi.headers["X-Cache"] = "HIT"
            # Add client-side caching headers
            roi.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            roi.headers["ETag"] = (
                f'"{generate_roi_cache_key(url, left, top, right, bottom, ms)}"'
            )
            return roi

        # Only misses (the actual fetch/encode work) go through the bounded
        # gate; a cache hit above is cheap and shouldn't be throttled by it.
        self._crop_gate.acquire()
        try:
            # Fetch the image or video frame
            if is_url_video(url):
                image = self.fetch_video_frame(url, ms)
            else:
                image = self.fetch_image(url)

            # Crop
            with image:  # ensure image is closed after use
                cropped_image = image.crop((left, top, right, bottom))

                # Convert to byte array
                with BytesIO() as img_byte_arr:
                    cropped_image.save(img_byte_arr, format="PNG")
                    img_data = img_byte_arr.getvalue()

            # Cache
            roi = CachedROI(img_data)
            roi.headers["X-Cache"] = "MISS"
            # Add client-side caching headers
            roi.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            roi.headers["ETag"] = (
                f'"{generate_roi_cache_key(url, left, top, right, bottom, ms)}"'
            )
            self._cache.set_roi(roi, url, left, top, right, bottom, ms=ms)

            return roi
        finally:
            self._crop_gate.release()

    async def fetch_image_async(self, url: str) -> Image.Image:
        """
        Fetch image from the given URL asynchronously.

        Args:
            url (str): The URL of the image.

        Returns:
            Image.Image: The fetched image.

        Raises:
            InvalidURLError: If the URL is invalid.
        """
        if not is_valid_url(url):
            raise InvalidURLError(f"Invalid URL: {url}")

        # Check for a cache hit
        image = self._cache.get_image(url)
        if image is not None:
            return image

        # Fetch the image
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

        # Convert and cache
        image_bytes = response.content
        with BytesIO(image_bytes) as img_buffer:
            image = Image.open(img_buffer)
            image.load()
            self._cache.set_image(image, url)
            return image

    async def fetch_video_frame_async(self, url: str, ms: int) -> Image.Image:
        """
        Fetch a video frame using Beholder asynchronously.

        Args:
            url (str): The URL of the video.
            ms (int): The timestamp into the video in milliseconds.

        Returns:
            Image.Image: The fetched video frame.

        Raises:
            InvalidURLError: If the URL is invalid.
            BeholderNotConfiguredError: If Beholder client is not configured.
        """
        if not is_valid_url(url):
            raise InvalidURLError(f"Invalid URL: {url}")

        # Check for Beholder configuration
        if self._beholder_client is None:
            raise BeholderNotConfiguredError(
                "Beholder client is not configured. Set BEHOLDER_URL and BEHOLDER_API_KEY."
            )

        # Check for a cache hit
        image = self._cache.get_image(url, ms=ms)
        if image is not None:
            return image

        # Fetch the frame and convert
        image = await self._beholder_client.capture_async(url, ms)

        # Cache
        self._cache.set_image(image, url, ms=ms)

        return image

    async def generate_crop_async(
        self, url: str, left: int, top: int, right: int, bottom: int, ms: int = 0
    ) -> CachedROI:
        """
        Generate a crop from the given URL based on the provided coordinates asynchronously.

        Args:
            url (str): The URL of the image or video.
            left (int): The left coordinate of the crop box.
            top (int): The top coordinate of the crop box.
            right (int): The right coordinate of the crop box.
            bottom (int): The bottom coordinate of the crop box.
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

        Returns:
            CachedROI: The cropped image byte array with custom headers.

        Raises:
            InvalidURLError: If the URL is invalid.
            InvalidCropParametersError: If the crop coordinates or timestamp are invalid.
            skimmer.backpressure.Saturated: If the crop pool has no room left.
            skimmer.backpressure.StaleWork: If the request waited too long for a slot.
        """
        if not is_valid_url(url):
            raise InvalidURLError(f"Invalid URL: {url}")
        validate_crop_parameters(left, top, right, bottom, ms)

        # Check for a cache hit
        roi = self._cache.get_roi(url, left, top, right, bottom, ms=ms)
        if roi is not None:
            roi.headers["X-Cache"] = "HIT"
            # Add client-side caching headers
            roi.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            roi.headers["ETag"] = (
                f'"{generate_roi_cache_key(url, left, top, right, bottom, ms)}"'
            )
            return roi

        # Only misses (the actual fetch/encode work) go through the bounded
        # gate; a cache hit above is cheap and shouldn't be throttled by it.
        await self._crop_gate_async.acquire()
        try:
            # Fetch the image or video frame
            if is_url_video(url):
                image = await self.fetch_video_frame_async(url, ms)
            else:
                image = await self.fetch_image_async(url)

            # Crop
            with image:  # ensure image is closed after use
                cropped_image = image.crop((left, top, right, bottom))

                # Convert to byte array
                with BytesIO() as img_byte_arr:
                    cropped_image.save(img_byte_arr, format="PNG")
                    img_data = img_byte_arr.getvalue()

            # Cache
            roi = CachedROI(img_data)
            roi.headers["X-Cache"] = "MISS"
            # Add client-side caching headers
            roi.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            roi.headers["ETag"] = (
                f'"{generate_roi_cache_key(url, left, top, right, bottom, ms)}"'
            )
            self._cache.set_roi(roi, url, left, top, right, bottom, ms=ms)

            return roi
        finally:
            self._crop_gate_async.release()

    def clear_cache(self) -> None:
        """
        Clear the cache.
        """
        self._cache.clear()
