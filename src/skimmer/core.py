import httpx
from io import BytesIO
from beholder_client import BeholderClient
from PIL import Image

from skimmer.cache import CacheController, CachedROI
from skimmer.config import BEHOLDER_API_KEY, BEHOLDER_URL
from skimmer.exceptions import BeholderNotConfiguredError, InvalidURLError
from skimmer.utils import is_url_video, is_valid_url


class Skimmer:
    def __init__(self):
        self._cache = CacheController()
        self._beholder_client = None
        if BEHOLDER_URL is not None and BEHOLDER_API_KEY is not None:
            self._beholder_client = BeholderClient(BEHOLDER_URL, BEHOLDER_API_KEY)

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
        response = httpx.get(url)
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
        """
        # Check for a cache hit
        roi = self._cache.get_roi(url, left, top, right, bottom, ms=ms)
        if roi is not None:
            roi.headers["X-Cache"] = "HIT"
            return roi

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
        self._cache.set_roi(roi, url, left, top, right, bottom, ms=ms)

        return roi

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
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
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
        """
        # Check for a cache hit
        roi = self._cache.get_roi(url, left, top, right, bottom, ms=ms)
        if roi is not None:
            roi.headers["X-Cache"] = "HIT"
            return roi

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
        self._cache.set_roi(roi, url, left, top, right, bottom, ms=ms)

        return roi

    def clear_cache(self) -> None:
        """
        Clear the cache.
        """
        self._cache.clear()
