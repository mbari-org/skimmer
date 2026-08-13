import shutil

import httpx
import pytest
from PIL import Image

from skimmer import create_default_flask_app, Skimmer
from skimmer.cache import CachedROI, generate_roi_cache_key
from skimmer.config import CACHE_DIR


def _beholder_503(retry_after: str | None = "2.5") -> httpx.HTTPStatusError:
    """Build the error beholder_client raises when Beholder itself sheds load."""
    request = httpx.Request("POST", "https://beholder.example/capture")
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    response = httpx.Response(503, headers=headers, request=request)
    return httpx.HTTPStatusError("busy", request=request, response=response)


@pytest.fixture
def client():
    app = create_default_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_cache():
    Skimmer()._cache.clear()
    shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def test_fetch_image(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    skimmer = Skimmer()
    image = skimmer.fetch_image(url)
    assert isinstance(image, Image.Image)


def test_fetch_image_reuses_http_client(mocker):
    """The sync fetch path should reuse one pooled httpx.Client, not open a new one per call."""
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mock_get = mocker.patch("httpx.Client.get", return_value=mock_response)

    skimmer = Skimmer()
    client = skimmer._http_client

    skimmer.fetch_image("https://example.com/image1.png")
    skimmer.fetch_image("https://example.com/image2.png")

    # Same client instance used across both calls
    assert skimmer._http_client is client
    assert mock_get.call_count == 2


def test_crop_image_miss(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    skimmer = Skimmer()
    cropped_image = skimmer.generate_crop(url, left, top, right, bottom)
    assert isinstance(cropped_image, CachedROI)
    assert cropped_image.headers["X-Cache"] == "MISS"


def test_crop_image_caching_headers(mocker):
    """Test that client-side caching headers are properly set."""
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    skimmer = Skimmer()
    cropped_image = skimmer.generate_crop(url, left, top, right, bottom)

    # Verify standard cache status
    assert isinstance(cropped_image, CachedROI)
    assert cropped_image.headers["X-Cache"] == "MISS"

    # Verify client-side caching headers
    assert "Cache-Control" in cropped_image.headers
    assert "ETag" in cropped_image.headers
    assert (
        cropped_image.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    )

    # Verify ETag format (should be quoted and contain the expected hash)
    etag = cropped_image.headers["ETag"]
    assert etag.startswith('"') and etag.endswith('"')
    assert len(etag) > 2  # More than just quotes

    # Test cache hit case to ensure headers are still present
    cropped_image_hit = skimmer.generate_crop(url, left, top, right, bottom)
    assert cropped_image_hit.headers["X-Cache"] == "HIT"
    assert "Cache-Control" in cropped_image_hit.headers
    assert "ETag" in cropped_image_hit.headers
    assert (
        cropped_image_hit.headers["Cache-Control"]
        == "public, max-age=31536000, immutable"
    )

    # ETag should be the same for same parameters
    assert cropped_image_hit.headers["ETag"] == cropped_image.headers["ETag"]


def test_crop_endpoint_miss(client, mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    response = client.get(f"/crop?url={url}&left=10&top=10&right=100&bottom=100")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers["X-Cache"] == "MISS"


def test_crop_endpoint_caching_headers(client, mocker):
    """Test that client-side caching headers are properly returned by the endpoint."""
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    response = client.get(f"/crop?url={url}&left=10&top=10&right=100&bottom=100")
    assert response.status_code == 200
    assert response.mimetype == "image/png"

    # Verify all caching headers are present in HTTP response
    assert "X-Cache" in response.headers
    assert "Cache-Control" in response.headers
    assert "ETag" in response.headers

    # Verify header values
    assert response.headers["X-Cache"] == "MISS"
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"

    # Verify ETag format
    etag = response.headers["ETag"]
    assert etag.startswith('"') and etag.endswith('"')
    assert len(etag) > 2  # More than just quotes


def test_crop_endpoint_hit(client, mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    client.get(
        f"/crop?url={url}&left=10&top=10&right=100&bottom=100"
    )  # First call to cache the image
    response = client.get(
        f"/crop?url={url}&left=10&top=10&right=100&bottom=100"
    )  # Second call should hit the cache
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers["X-Cache"] == "HIT"

    # Verify caching headers are still present on cache hit
    assert "Cache-Control" in response.headers
    assert "ETag" in response.headers
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_cache_eviction(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    initial_key = generate_roi_cache_key(f"{url}?id=1", left, top, right, bottom)
    skimmer = Skimmer()
    cache = skimmer._cache
    skimmer.generate_crop(f"{url}?id=1", left, top, right, bottom)

    i = 2
    while initial_key in cache._roi_cache:
        skimmer.generate_crop(f"{url}?id={i}", left, top, right, bottom)
        i += 1

    cropped_image = skimmer.generate_crop(url, left, top, right, bottom)
    assert isinstance(cropped_image, CachedROI)
    assert cropped_image.headers["X-Cache"] == "MISS"


def test_filesystem_cache_persistence(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    skimmer = Skimmer()
    cache = skimmer._cache
    skimmer.generate_crop(url, left, top, right, bottom)  # Cache the image
    roi = cache.get_roi(url, left, top, right, bottom)
    assert roi is not None  # Ensure the image is cached in the filesystem
    cache._roi_cache.expire()  # Ensure expired items are removed
    roi = skimmer.generate_crop(
        url, left, top, right, bottom
    )  # Should hit the filesystem cache
    assert isinstance(roi, CachedROI)
    assert roi.headers["X-Cache"] == "HIT"


def test_invalid_url_error(client):
    response = client.get("/crop?url=invalid_url&left=10&top=10&right=100&bottom=100")
    assert response.status_code == 400
    assert response.json == {"error": "Invalid URL: invalid_url"}


def test_crop_endpoint_invalid_coordinates_no_fetch(client, mocker):
    mock_get = mocker.patch("httpx.Client.get")

    response = client.get(
        "/crop?url=https://example.com/image.png&left=100&top=10&right=10&bottom=100"
    )
    assert response.status_code == 400
    assert response.json == {
        "error": "right (10) must be greater than left (100)"
    }
    mock_get.assert_not_called()


def test_crop_endpoint_negative_coordinates_no_fetch(client, mocker):
    mock_get = mocker.patch("httpx.Client.get")

    response = client.get(
        "/crop?url=https://example.com/image.png&left=-10&top=10&right=100&bottom=100"
    )
    assert response.status_code == 400
    assert "non-negative" in response.json["error"]
    mock_get.assert_not_called()


def test_crop_endpoint_missing_coordinates(client, mocker):
    mock_get = mocker.patch("httpx.Client.get")

    response = client.get("/crop?url=https://example.com/image.png&left=10&top=10")
    assert response.status_code == 400
    mock_get.assert_not_called()


def test_generate_crop_invalid_coordinates_no_fetch(mocker):
    from skimmer.exceptions import InvalidCropParametersError

    mock_get = mocker.patch("httpx.Client.get")
    url = "https://example.com/image.png"

    skimmer = Skimmer()
    with pytest.raises(InvalidCropParametersError):
        skimmer.generate_crop(url, 100, 10, 10, 100)
    mock_get.assert_not_called()


def test_beholder_not_configured_error(client, mocker):
    url = "https://example.com/video.mp4"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)

    response = client.get(
        f"/crop?url={url}&left=10&top=10&right=100&bottom=100&ms=1000"
    )
    assert response.status_code == 500
    assert response.json == {
        "error": "Beholder client is not configured. Set BEHOLDER_URL and BEHOLDER_API_KEY."
    }


def test_unexpected_error(client, mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.Client.get", return_value=mock_response)
    mocker.patch(
        "skimmer.core.Skimmer.generate_crop", side_effect=Exception("Unexpected error")
    )

    response = client.get(f"/crop?url={url}&left=10&top=10&right=100&bottom=100")
    assert response.status_code == 500
    assert response.json == {"error": "An unexpected error occurred: Unexpected error"}


def test_beholder_503_is_forwarded_as_skimmer_503(client, mocker):
    """A 503 from Beholder (via beholder_client) must surface as Skimmer's own 503,
    not the generic 500 catch-all, so callers can retry with the right Retry-After."""
    url = "https://example.com/video.mp4"
    mocker.patch(
        "skimmer.core.Skimmer.generate_crop", side_effect=_beholder_503("2.5")
    )

    response = client.get(
        f"/crop?url={url}&left=10&top=10&right=100&bottom=100&ms=1000"
    )
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "2.5"


def test_beholder_503_without_retry_after_falls_back_to_default(client, mocker):
    mocker.patch(
        "skimmer.core.Skimmer.generate_crop", side_effect=_beholder_503(None)
    )

    response = client.get(
        "/crop?url=https://example.com/video.mp4&left=10&top=10&right=100&bottom=100&ms=1000"
    )
    assert response.status_code == 503
    assert 1.0 <= float(response.headers["Retry-After"]) <= 3.0


def test_beholder_non_503_error_is_not_treated_as_busy(client, mocker):
    request = httpx.Request("POST", "https://beholder.example/capture")
    error = httpx.HTTPStatusError(
        "boom", request=request, response=httpx.Response(500, request=request)
    )
    mocker.patch("skimmer.core.Skimmer.generate_crop", side_effect=error)

    response = client.get(
        "/crop?url=https://example.com/video.mp4&left=10&top=10&right=100&bottom=100&ms=1000"
    )
    assert response.status_code == 500
    assert "Retry-After" not in response.headers


def test_fetch_image_with_redirect(mocker):
    """Test that the shared httpx.Client follows redirects (e.g., 307 Temporary Redirect)."""
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()

    mock_get = mocker.patch("httpx.Client.get", return_value=mock_response)

    skimmer = Skimmer()

    # follow_redirects is configured on the shared client, not per-request
    assert skimmer._http_client.follow_redirects is True

    image = skimmer.fetch_image(url)

    # Verify the image was fetched successfully
    assert isinstance(image, Image.Image)
    mock_get.assert_called_once_with(url)


def test_crop_endpoint_with_redirect(client, mocker):
    """Test that the /crop endpoint handles redirects properly."""
    url = "https://example.com/redirect-image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()

    mock_get = mocker.patch("httpx.Client.get", return_value=mock_response)

    response = client.get(f"/crop?url={url}&left=10&top=10&right=100&bottom=100")

    # Verify the request was successful
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    mock_get.assert_called_once_with(url)


@pytest.mark.asyncio
async def test_fetch_image_async_with_redirect(mocker):
    """Test that async httpx.AsyncClient.get follows redirects."""
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()

    # Mock AsyncClient's get method
    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    skimmer = Skimmer()
    image = await skimmer.fetch_image_async(url)

    # Verify the image was fetched successfully
    assert isinstance(image, Image.Image)

    # Verify that client.get was called with follow_redirects=True
    mock_client.get.assert_called_once_with(url, follow_redirects=True)


@pytest.mark.asyncio
async def test_fetch_video_frame_async_returns_image(mocker):
    """fetch_video_frame_async must return the captured frame (regression test)."""
    url = "https://example.com/video.mp4"
    ms = 1000
    frame = Image.open("tests/test_image.png")
    frame.load()

    skimmer = Skimmer()
    skimmer._beholder_client = mocker.Mock()
    skimmer._beholder_client.capture_async = mocker.AsyncMock(return_value=frame)

    image = await skimmer.fetch_video_frame_async(url, ms)

    assert image is frame
    # Subsequent calls should hit the image cache instead of calling Beholder again
    cached_image = await skimmer.fetch_video_frame_async(url, ms)
    assert cached_image is frame
    skimmer._beholder_client.capture_async.assert_called_once_with(url, ms)
