import shutil

import pytest
from PIL import Image

from skimmer import create_default_flask_app, Skimmer
from skimmer.cache import CachedROI, generate_roi_cache_key
from skimmer.config import CACHE_DIR


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
    mocker.patch("httpx.get", return_value=mock_response)

    skimmer = Skimmer()
    image = skimmer.fetch_image(url)
    assert isinstance(image, Image.Image)


def test_crop_image_miss(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    skimmer = Skimmer()
    cropped_image = skimmer.generate_crop(url, left, top, right, bottom)
    assert isinstance(cropped_image, CachedROI)
    assert cropped_image.headers["X-Cache"] == "MISS"


def test_crop_endpoint_miss(client, mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.get", return_value=mock_response)

    response = client.get(f"/crop?url={url}&left=10&top=10&right=100&bottom=100")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers["X-Cache"] == "MISS"


def test_crop_endpoint_hit(client, mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.get", return_value=mock_response)

    client.get(
        f"/crop?url={url}&left=10&top=10&right=100&bottom=100"
    )  # First call to cache the image
    response = client.get(
        f"/crop?url={url}&left=10&top=10&right=100&bottom=100"
    )  # Second call should hit the cache
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers["X-Cache"] == "HIT"


def test_cache_eviction(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    initial_key = generate_roi_cache_key(f"{url}?id=1", left, top, right, bottom)
    skimmer = Skimmer()
    cache = skimmer._cache
    skimmer.generate_crop(f"{url}?id=1", left, top, right, bottom)

    i = 2
    while cache._roi_cache.get(initial_key) is not None:
        skimmer.generate_crop(f"{url}?id={i}", left, top, right, bottom)
        i += 1

    cropped_image = skimmer.generate_crop(url, left, top, right, bottom)
    assert isinstance(cropped_image, CachedROI)
    assert cropped_image.headers["X-Cache"] == "MISS"


def test_filesystem_cache_persistence(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.get", return_value=mock_response)

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


def test_beholder_not_configured_error(client, mocker):
    url = "https://example.com/video.mp4"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("httpx.get", return_value=mock_response)

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
    mocker.patch("httpx.get", return_value=mock_response)
    mocker.patch(
        "skimmer.core.Skimmer.generate_crop", side_effect=Exception("Unexpected error")
    )

    response = client.get(f"/crop?url={url}&left=10&top=10&right=100&bottom=100")
    assert response.status_code == 500
    assert response.json == {"error": "An unexpected error occurred: Unexpected error"}
