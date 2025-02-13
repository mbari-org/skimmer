import pytest
from skimmer import (
    create_app,
    fetch_image,
    crop_image,
    roi_cache,
    CachedImage,
    generate_cache_key,
)
from skimmer.config import CACHE_DIR
from PIL import Image
import shutil


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_cache():
    roi_cache.clear()
    shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def test_fetch_image(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("requests.get", return_value=mock_response)

    image = fetch_image(url)
    assert isinstance(image, Image.Image)


def test_crop_image_miss(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("requests.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    cropped_image = crop_image(url, left, top, right, bottom)
    assert isinstance(cropped_image, CachedImage)
    assert cropped_image.headers["X-Cache"] == "MISS"


def test_crop_endpoint_miss(client, mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("requests.get", return_value=mock_response)

    response = client.get(f"/crop?url={url}&left=10&top=10&right=100&bottom=100")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers["X-Cache"] == "MISS"


def test_crop_endpoint_hit(client, mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("requests.get", return_value=mock_response)

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
    mocker.patch("requests.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    initial_key = generate_cache_key(f"{url}?id=1", left, top, right, bottom)
    crop_image(f"{url}?id=1", left, top, right, bottom)

    i = 2
    while roi_cache.get(initial_key) is not None:
        crop_image(f"{url}?id={i}", left, top, right, bottom)
        i += 1

    cropped_image = crop_image(url, left, top, right, bottom)
    assert isinstance(cropped_image, CachedImage)
    assert cropped_image.headers["X-Cache"] == "MISS"


def test_filesystem_cache_persistence(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("requests.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    crop_image(url, left, top, right, bottom)  # Cache the image
    cached_image = roi_cache.get(generate_cache_key(url, left, top, right, bottom))
    assert cached_image is not None  # Ensure the image is cached in the filesystem
    roi_cache.expire()  # Ensure expired items are removed
    cropped_image = crop_image(
        url, left, top, right, bottom
    )  # Should hit the filesystem cache
    assert isinstance(cropped_image, CachedImage)
    assert cropped_image.headers["X-Cache"] == "HIT"
