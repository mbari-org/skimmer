from flask import Flask, request, send_file, Response
from io import BytesIO
from PIL import Image
import requests
from diskcache import Cache
from cachetools import LRUCache
import hashlib
from skimmer.config import (
    IMAGE_CACHE_SIZE_MB,
    ROI_CACHE_SIZE_MB,
    CACHE_DIR,
    APP_HOST,
    APP_PORT,
    APP_DEBUG,
)

app = Flask(__name__)

# Initialize diskcache for ROIs
roi_cache = Cache(CACHE_DIR, size_limit=ROI_CACHE_SIZE_MB * 1024 ** 2)
roi_cache.expire()  # Ensure expired items are removed

# In-memory cache for full images
full_image_cache = LRUCache(maxsize=IMAGE_CACHE_SIZE_MB * 1024 ** 2, getsizeof=lambda image: len(image.tobytes()))

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


def fetch_image(url: str) -> Image.Image:
    """
    Fetch image from the given URL.

    Args:
        url (str): The URL of the image.

    Returns:
        Image.Image: The fetched image.
    """
    if url in full_image_cache:
        return full_image_cache[url]

    response = requests.get(url)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    full_image_cache[url] = image
    return image


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
    cached_image = roi_cache.get(cache_key)
    if cached_image:
        cached_image.headers["X-Cache"] = "HIT"
        return cached_image

    image = fetch_image(url)
    cropped_image = image.crop((left, top, right, bottom))
    img_byte_arr = BytesIO()
    cropped_image.save(img_byte_arr, format="PNG")
    img_data = img_byte_arr.getvalue()
    cached_image = CachedImage(img_data)
    cached_image.headers["X-Cache"] = "MISS"
    roi_cache.set(cache_key, cached_image)
    return cached_image


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

    cropped_image = crop_image(url, left, top, right, bottom)
    response = send_file(BytesIO(cropped_image.get_data()), mimetype="image/png")
    response.headers["X-Cache"] = cropped_image.headers["X-Cache"]
    return response


def main() -> None:
    """
    Run the Flask application.
    """
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
