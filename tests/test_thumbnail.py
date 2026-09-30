from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from skimmer import Skimmer, create_default_fastapi_app
from skimmer.backpressure import Saturated
from skimmer.config import THUMBNAIL_SIZES
from skimmer.exceptions import InvalidThumbnailParametersError, InvalidURLError
from skimmer.thumbnail import decode_for_thumbnail, render_thumbnail
from skimmer.utils import resolve_thumbnail_size

IMAGE_URL = "https://example.com/image.jpg"
VIDEO_URL = "https://example.com/video.mp4"


def _encode(image: Image.Image, format: str) -> bytes:
    with BytesIO() as buffer:
        image.save(buffer, format=format)
        return buffer.getvalue()


def _decode(data: bytes) -> Image.Image:
    image = Image.open(BytesIO(data))
    image.load()
    return image


@pytest.fixture
def large_jpeg() -> bytes:
    return _encode(Image.new("RGB", (4000, 3000), (10, 120, 200)), "JPEG")


@pytest.fixture
def mock_download(mocker, large_jpeg):
    return mocker.patch.object(Skimmer, "_download", return_value=large_jpeg)


# --- render_thumbnail / decode_for_thumbnail


def test_render_thumbnail_fits_longest_edge_and_keeps_aspect():
    image = Image.new("RGB", (4000, 3000))
    thumb = _decode(render_thumbnail(image, 256, 85))
    assert thumb.format == "JPEG"
    assert thumb.size == (256, 192)


def test_render_thumbnail_portrait():
    thumb = _decode(render_thumbnail(Image.new("RGB", (300, 1200)), 128, 85))
    assert thumb.size == (32, 128)


def test_render_thumbnail_does_not_upscale():
    thumb = _decode(render_thumbnail(Image.new("RGB", (100, 50)), 512, 85))
    assert thumb.size == (100, 50)


def test_render_thumbnail_does_not_mutate_input():
    image = Image.new("RGBA", (1000, 1000))
    render_thumbnail(image, 128, 85)
    assert image.size == (1000, 1000)
    assert image.mode == "RGBA"


@pytest.mark.parametrize(
    "mode,expected", [("RGBA", "RGB"), ("P", "RGB"), ("LA", "L"), ("L", "L")]
)
def test_render_thumbnail_converts_modes_jpeg_cannot_encode(mode, expected):
    thumb = _decode(render_thumbnail(Image.new(mode, (400, 400)), 128, 85))
    assert thumb.mode == expected


def test_decode_for_thumbnail_uses_jpeg_draft(large_jpeg):
    image = decode_for_thumbnail(large_jpeg, 256)
    # Draft decodes at a reduced DCT scale but never below the target size
    assert image.size[0] < 4000
    assert min(image.size) >= 256


def test_decode_for_thumbnail_non_jpeg_decodes_full():
    data = _encode(Image.new("RGB", (800, 600)), "PNG")
    assert decode_for_thumbnail(data, 128).size == (800, 600)


# --- parameter validation


def test_resolve_thumbnail_size():
    assert resolve_thumbnail_size("small", {"small": 64}, 0) == 64


def test_resolve_thumbnail_size_unknown():
    with pytest.raises(InvalidThumbnailParametersError):
        resolve_thumbnail_size("huge", {"small": 64}, 0)


def test_resolve_thumbnail_size_negative_ms():
    with pytest.raises(InvalidThumbnailParametersError):
        resolve_thumbnail_size("small", {"small": 64}, -1)


# --- Skimmer.generate_thumbnail


def test_generate_thumbnail_miss_then_hit(mock_download):
    skimmer = Skimmer()
    miss = skimmer.generate_thumbnail(IMAGE_URL, size="small")
    assert miss.media_type == "image/jpeg"
    assert miss.headers["X-Cache"] == "MISS"
    assert max(_decode(miss.get_data()).size) == THUMBNAIL_SIZES["small"]

    hit = skimmer.generate_thumbnail(IMAGE_URL, size="small")
    assert hit.headers["X-Cache"] == "HIT"
    assert hit.headers["ETag"] == miss.headers["ETag"]
    assert hit.get_data() == miss.get_data()
    mock_download.assert_called_once_with(IMAGE_URL)


def test_generate_thumbnail_persists_across_instances(mock_download):
    Skimmer().generate_thumbnail(IMAGE_URL)
    assert Skimmer().generate_thumbnail(IMAGE_URL).headers["X-Cache"] == "HIT"


def test_generate_thumbnail_sizes_cached_separately(mock_download):
    skimmer = Skimmer()
    small = skimmer.generate_thumbnail(IMAGE_URL, size="small")
    large = skimmer.generate_thumbnail(IMAGE_URL, size="large")
    assert small.headers["ETag"] != large.headers["ETag"]
    assert large.headers["X-Cache"] == "MISS"


def test_generate_thumbnail_does_not_populate_image_cache(mock_download):
    skimmer = Skimmer()
    skimmer.generate_thumbnail(IMAGE_URL)
    assert skimmer._cache.get_image(IMAGE_URL) is None


def test_generate_thumbnail_reuses_cached_source(mock_download):
    skimmer = Skimmer()
    source = Image.new("RGB", (640, 480))
    skimmer._cache.set_image(source, IMAGE_URL)

    thumbnail = skimmer.generate_thumbnail(IMAGE_URL, size="small")

    mock_download.assert_not_called()
    assert _decode(thumbnail.get_data()).size == (128, 96)
    # Cached source is left intact for later crops
    assert source.size == (640, 480)


def test_generate_thumbnail_invalid_url_no_fetch(mock_download):
    with pytest.raises(InvalidURLError):
        Skimmer().generate_thumbnail("not-a-url")
    mock_download.assert_not_called()


def test_generate_thumbnail_video_frame_not_cached(mocker):
    skimmer = Skimmer()
    skimmer._beholder_client = mocker.Mock()
    skimmer._beholder_client.capture.return_value = Image.new("RGB", (1920, 1080))

    thumbnail = skimmer.generate_thumbnail(VIDEO_URL, size="medium", ms=1000)

    skimmer._beholder_client.capture.assert_called_once_with(VIDEO_URL, 1000)
    assert _decode(thumbnail.get_data()).size == (256, 144)
    assert skimmer._cache.get_image(VIDEO_URL, ms=1000) is None


@pytest.mark.asyncio
async def test_generate_thumbnail_async_miss_then_hit(mocker, large_jpeg):
    mock_download = mocker.patch.object(
        Skimmer, "_download_async", return_value=large_jpeg
    )
    skimmer = Skimmer()
    miss = await skimmer.generate_thumbnail_async(IMAGE_URL, size="small")
    hit = await skimmer.generate_thumbnail_async(IMAGE_URL, size="small")
    assert miss.headers["X-Cache"] == "MISS"
    assert hit.headers["X-Cache"] == "HIT"
    mock_download.assert_called_once_with(IMAGE_URL)


# --- Flask endpoint


def test_thumbnail_endpoint(client, mock_download):
    response = client.get(f"/thumbnail?url={IMAGE_URL}&size=small")
    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
    assert response.headers["X-Cache"] == "MISS"
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert max(_decode(response.data).size) == THUMBNAIL_SIZES["small"]

    response = client.get(f"/thumbnail?url={IMAGE_URL}&size=small")
    assert response.headers["X-Cache"] == "HIT"


def test_thumbnail_endpoint_default_size(client, mock_download):
    response = client.get(f"/thumbnail?url={IMAGE_URL}")
    assert response.status_code == 200
    assert max(_decode(response.data).size) == THUMBNAIL_SIZES["medium"]


def test_thumbnail_endpoint_invalid_size(client, mock_download):
    response = client.get(f"/thumbnail?url={IMAGE_URL}&size=huge")
    assert response.status_code == 400
    assert "size" in response.json["error"]
    mock_download.assert_not_called()


def test_thumbnail_endpoint_invalid_ms(client, mock_download):
    response = client.get(f"/thumbnail?url={IMAGE_URL}&ms=abc")
    assert response.status_code == 400


def test_thumbnail_endpoint_missing_url(client, mock_download):
    response = client.get("/thumbnail")
    assert response.status_code == 400


def test_thumbnail_endpoint_saturated(client, mocker, mock_download):
    mocker.patch("skimmer.backpressure.BoundedGate.acquire", side_effect=Saturated)
    response = client.get(f"/thumbnail?url={IMAGE_URL}")
    assert response.status_code == 503
    assert "Retry-After" in response.headers


# --- FastAPI endpoint


def test_fastapi_thumbnail_endpoint(mocker, large_jpeg):
    mocker.patch.object(Skimmer, "_download_async", return_value=large_jpeg)
    client = TestClient(create_default_fastapi_app())

    response = client.get("/thumbnail", params={"url": IMAGE_URL, "size": "large"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["X-Cache"] == "MISS"
    assert max(_decode(response.content).size) == THUMBNAIL_SIZES["large"]


def test_fastapi_thumbnail_endpoint_invalid_size():
    client = TestClient(create_default_fastapi_app())
    response = client.get("/thumbnail", params={"url": IMAGE_URL, "size": "huge"})
    assert response.status_code == 400
