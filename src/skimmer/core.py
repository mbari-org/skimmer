import httpx
from io import BytesIO
from beholder_client import BeholderClient
from PIL import Image

from skimmer.backpressure import AsyncBoundedGate, BoundedGate
from skimmer.cache import (
    CacheController,
    CachedImage,
    generate_roi_cache_key,
    generate_thumbnail_cache_key,
)
from skimmer.config import (
    BEHOLDER_API_KEY,
    BEHOLDER_URL,
    CROP_POOL_MAX_WAIT_SECONDS,
    CROP_POOL_QUEUE_SIZE,
    CROP_POOL_SLOTS,
    THUMBNAIL_JPEG_QUALITY,
    THUMBNAIL_DEFAULT_SIZE,
    THUMBNAIL_SIZES,
)
from skimmer.exceptions import BeholderNotConfiguredError, InvalidURLError
from skimmer.thumbnail import decode_for_thumbnail, render_thumbnail
from skimmer.utils import (
    is_url_video,
    is_valid_url,
    resolve_thumbnail_size,
    validate_crop_parameters,
)


HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
CACHE_CONTROL = "public, max-age=31536000, immutable"


def _set_response_headers(image: CachedImage, etag: str, hit: bool) -> CachedImage:
    """Set cache status and client-side caching headers on a cached image."""
    image.headers["X-Cache"] = "HIT" if hit else "MISS"
    image.headers["Cache-Control"] = CACHE_CONTROL
    image.headers["ETag"] = f'"{etag}"'
    return image


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

        # Bounds concurrent crop/thumbnail generation the same way Beholder bounds
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

    def _download(self, url: str) -> bytes:
        """Download raw bytes from the given URL."""
        response = self._http_client.get(url)
        response.raise_for_status()
        return response.content

    async def _download_async(self, url: str) -> bytes:
        """Download raw bytes from the given URL asynchronously."""
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
        return response.content

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
        image_bytes = self._download(url)

        # Convert and cache
        with BytesIO(image_bytes) as img_buffer:
            image = Image.open(img_buffer)
            image.load()
            self._cache.set_image(image, url)
            return image

    def fetch_video_frame(
        self, url: str, ms: int, cache_result: bool = True
    ) -> Image.Image:
        """
        Fetch a video frame using Beholder.

        Args:
            url (str): The URL of the video.
            ms (int): The timestamp into the video in milliseconds.
            cache_result (bool): Whether to store a freshly fetched frame in the
                in-memory image cache.

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
        if cache_result:
            self._cache.set_image(image, url, ms=ms)

        return image

    def generate_crop(
        self, url: str, left: int, top: int, right: int, bottom: int, ms: int = 0
    ) -> CachedImage:
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
            CachedImage: The cropped image byte array with custom headers.

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
        etag = generate_roi_cache_key(url, left, top, right, bottom, ms)
        if roi is not None:
            return _set_response_headers(roi, etag, hit=True)

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
            roi = _set_response_headers(CachedImage(img_data), etag, hit=False)
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
        image_bytes = await self._download_async(url)

        # Convert and cache
        with BytesIO(image_bytes) as img_buffer:
            image = Image.open(img_buffer)
            image.load()
            self._cache.set_image(image, url)
            return image

    async def fetch_video_frame_async(
        self, url: str, ms: int, cache_result: bool = True
    ) -> Image.Image:
        """
        Fetch a video frame using Beholder asynchronously.

        Args:
            url (str): The URL of the video.
            ms (int): The timestamp into the video in milliseconds.
            cache_result (bool): Whether to store a freshly fetched frame in the
                in-memory image cache.

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
        if cache_result:
            self._cache.set_image(image, url, ms=ms)

        return image

    async def generate_crop_async(
        self, url: str, left: int, top: int, right: int, bottom: int, ms: int = 0
    ) -> CachedImage:
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
            CachedImage: The cropped image byte array with custom headers.

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
        etag = generate_roi_cache_key(url, left, top, right, bottom, ms)
        if roi is not None:
            return _set_response_headers(roi, etag, hit=True)

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
            roi = _set_response_headers(CachedImage(img_data), etag, hit=False)
            self._cache.set_roi(roi, url, left, top, right, bottom, ms=ms)

            return roi
        finally:
            self._crop_gate_async.release()

    def _check_thumbnail_cache(
        self, url: str, size: str, ms: int
    ) -> tuple[int, str, CachedImage | None]:
        """Validate thumbnail parameters and look up a cached thumbnail.

        Returns:
            tuple[int, str, CachedImage | None]: The max edge, ETag, and cached
            thumbnail (with headers set) or None on a miss.
        """
        if not is_valid_url(url):
            raise InvalidURLError(f"Invalid URL: {url}")
        max_edge = resolve_thumbnail_size(size, THUMBNAIL_SIZES, ms)
        etag = generate_thumbnail_cache_key(url, max_edge, THUMBNAIL_JPEG_QUALITY, ms)
        thumbnail = self._cache.get_thumbnail(
            url, max_edge, THUMBNAIL_JPEG_QUALITY, ms=ms
        )
        if thumbnail is not None:
            thumbnail = _set_response_headers(thumbnail, etag, hit=True)
        return max_edge, etag, thumbnail

    def _store_thumbnail(
        self, source: Image.Image, url: str, max_edge: int, etag: str, ms: int
    ) -> CachedImage:
        """Render a thumbnail from its source image and cache it."""
        data = render_thumbnail(source, max_edge, THUMBNAIL_JPEG_QUALITY)
        thumbnail = _set_response_headers(
            CachedImage(data, media_type="image/jpeg"), etag, hit=False
        )
        self._cache.set_thumbnail(
            thumbnail, url, max_edge, THUMBNAIL_JPEG_QUALITY, ms=ms
        )
        return thumbnail

    def generate_thumbnail(
        self, url: str, size: str = THUMBNAIL_DEFAULT_SIZE, ms: int = 0
    ) -> CachedImage:
        """
        Generate a JPEG thumbnail of the full image or video frame at the given URL.

        Thumbnail sources are not added to the in-memory image cache: they are
        typically large and used once, and would evict images reused by crops.
        An already-cached source is reused, though.

        Args:
            url (str): The URL of the image or video.
            size (str): The size preset name (see THUMBNAIL_SIZES).
            ms (int): The timestamp into the video in milliseconds. For images, this should be 0.

        Returns:
            CachedImage: The JPEG thumbnail with custom headers.

        Raises:
            InvalidURLError: If the URL is invalid.
            InvalidThumbnailParametersError: If the size or timestamp is invalid.
            skimmer.backpressure.Saturated: If the pool has no room left.
            skimmer.backpressure.StaleWork: If the request waited too long for a slot.
        """
        max_edge, etag, thumbnail = self._check_thumbnail_cache(url, size, ms)
        if thumbnail is not None:
            return thumbnail

        self._crop_gate.acquire()
        try:
            if is_url_video(url):
                source = self.fetch_video_frame(url, ms, cache_result=False)
            else:
                source = self._cache.get_image(url)
                if source is None:
                    source = decode_for_thumbnail(self._download(url), max_edge)
            return self._store_thumbnail(source, url, max_edge, etag, ms)
        finally:
            self._crop_gate.release()

    async def generate_thumbnail_async(
        self, url: str, size: str = THUMBNAIL_DEFAULT_SIZE, ms: int = 0
    ) -> CachedImage:
        """
        Async equivalent of :meth:`generate_thumbnail`.
        """
        max_edge, etag, thumbnail = self._check_thumbnail_cache(url, size, ms)
        if thumbnail is not None:
            return thumbnail

        await self._crop_gate_async.acquire()
        try:
            if is_url_video(url):
                source = await self.fetch_video_frame_async(url, ms, cache_result=False)
            else:
                source = self._cache.get_image(url)
                if source is None:
                    source = decode_for_thumbnail(
                        await self._download_async(url), max_edge
                    )
            return self._store_thumbnail(source, url, max_edge, etag, ms)
        finally:
            self._crop_gate_async.release()

    def clear_cache(self) -> None:
        """
        Clear the cache.
        """
        self._cache.clear()
