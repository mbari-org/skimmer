import pytest
from skimmer import app, fetch_image, crop_image, cache, CachedImage
from skimmer.config import CACHE_DIR
from PIL import Image
import shutil


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
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
    assert cropped_image.headers["X-Cache-Source"] == "None"


def test_crop_endpoint_miss(client, mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("requests.get", return_value=mock_response)

    response = client.get(f"/crop?url={url}&left=10&top=10&right=100&bottom=100")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers["X-Cache"] == "MISS"
    assert response.headers["X-Cache-Source"] == "None"


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
    assert response.headers["X-Cache-Source"] == "Memory"


def test_cache_eviction(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("requests.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    for i in range(1, 102):  # Assuming CACHE_SIZE is 100
        crop_image(f"{url}?id={i}", left, top, right, bottom)

    cropped_image = crop_image(url, left, top, right, bottom)
    assert isinstance(cropped_image, CachedImage)
    assert cropped_image.headers["X-Cache"] == "MISS"
    assert cropped_image.headers["X-Cache-Source"] == "None"


def test_filesystem_cache_persistence(mocker):
    url = "https://example.com/image.png"
    mock_response = mocker.Mock()
    mock_response.content = open("tests/test_image.png", "rb").read()
    mocker.patch("requests.get", return_value=mock_response)

    left, top, right, bottom = 10, 10, 100, 100
    crop_image(url, left, top, right, bottom)  # Cache the image
    cache.clear()  # Clear the in-memory cache
    cropped_image = crop_image(
        url, left, top, right, bottom
    )  # Should hit the filesystem cache
    assert isinstance(cropped_image, CachedImage)
    assert cropped_image.headers["X-Cache"] == "HIT"
    assert cropped_image.headers["X-Cache-Source"] == "Filesystem"
