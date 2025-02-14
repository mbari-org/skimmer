from mimetypes import guess_type
from urllib.parse import urlparse


def is_url_video(url: str) -> bool:
    """
    Check if the URL points to a video file.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL points to a video file, False otherwise.
    """
    mime, _ = guess_type(url)
    return mime is not None and mime.startswith("video/")


def is_valid_url(url: str) -> bool:
    """
    Validate the given URL.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])
