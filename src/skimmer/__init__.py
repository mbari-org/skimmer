from flask import Flask, request, send_file, Response
from io import BytesIO
from PIL import Image
import requests
from cachetools import cached, TTLCache
import hashlib
from skimmer.config import (
    CACHE_SIZE,
    CACHE_TTL,
    CACHE_DIR,
    APP_HOST,
    APP_PORT,
    APP_DEBUG,
)

app = Flask(__name__)

cache = TTLCache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)


class CachedImage:
    def __init__(self, data: bytes):
        self.data = data
        self.headers = {}

    def get_data(self) -> bytes:
        return self.data


def generate_cache_key(url: str, left: int, top: int, right: int, bottom: int) -> str:
    """
    Generate a cache key based on URL and crop parameters.

    Args:
        url (str): The URL of the image.
        left (int): The left coordinate of the crop box.
        top (int): The top coordinate of the crop box.
        right (int): The right coordinate of the crop box.
        bottom (int): The bottom coordinate of the crop box.

    Returns:
        str: The generated cache key.
    """
    key = f"{url}_{left}_{top}_{right}_{bottom}"
    return hashlib.md5(key.encode()).hexdigest()


def save_to_filesystem_cache(key: str, img_data: bytes) -> None:
    """
    Save image to filesystem cache.

    Args:
        key (str): The cache key.
        img_data (bytes): The image byte array.
    """
    with (CACHE_DIR / key).open("wb") as f:
        f.write(img_data)


def load_from_filesystem_cache(key: str) -> CachedImage:
    """
    Load image from filesystem cache.

    Args:
        key (str): The cache key.

    Returns:
        CachedImage: The image byte array if found, else None.
    """
    file_path = CACHE_DIR / key
    if file_path.exists():
        with file_path.open("rb") as f:
            return CachedImage(f.read())
    return None


def fetch_image(url: str) -> Image.Image:
    """
    Fetch image from the given URL.

    Args:
        url (str): The URL of the image.

    Returns:
        Image.Image: The fetched image.
    """
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))


@cached(cache, key=generate_cache_key)
def crop_image(url: str, left: int, top: int, right: int, bottom: int) -> CachedImage:
    """
    Crop the image from the given URL based on the provided coordinates.

    Args:
        url (str): The URL of the image.
        left (int): The left coordinate of the crop box.
        top (int): The top coordinate of the crop box.
        right (int): The right coordinate of the crop box.
        bottom (int): The bottom coordinate of the crop box.

    Returns:
        CachedImage: The cropped image byte array.
    """
    cache_key = generate_cache_key(url, left, top, right, bottom)
    cached_image = load_from_filesystem_cache(cache_key)
    if cached_image:
        cached_image.headers["X-Cache"] = "HIT"
        cached_image.headers["X-Cache-Source"] = "Filesystem"
        return cached_image

    image = fetch_image(url)
    cropped_image = image.crop((left, top, right, bottom))
    img_byte_arr = BytesIO()
    cropped_image.save(img_byte_arr, format="PNG")
    img_data = img_byte_arr.getvalue()
    save_to_filesystem_cache(cache_key, img_data)
    img_byte_arr = CachedImage(img_data)
    img_byte_arr.headers["X-Cache"] = "MISS"
    img_byte_arr.headers["X-Cache-Source"] = "None"
    return img_byte_arr


@app.route("/crop", methods=["GET"])
def crop() -> Response:
    """
    Crop the image based on the provided URL and coordinates.

    Returns:
        Response: The cropped image with custom headers.
    """
    url = request.args.get("url")
    left = int(request.args.get("left"))
    top = int(request.args.get("top"))
    right = int(request.args.get("right"))
    bottom = int(request.args.get("bottom"))

    cache_key = generate_cache_key(url, left, top, right, bottom)
    if cache_key in cache:
        cached_image = cache[cache_key]
        response = send_file(BytesIO(cached_image.get_data()), mimetype="image/png")
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Source"] = "Memory"
        return response

    cropped_image = crop_image(url, left, top, right, bottom)
    response = send_file(BytesIO(cropped_image.get_data()), mimetype="image/png")
    response.headers["X-Cache"] = cropped_image.headers["X-Cache"]
    response.headers["X-Cache-Source"] = cropped_image.headers["X-Cache-Source"]
    return response


def main() -> None:
    """
    Run the Flask application.
    """
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
