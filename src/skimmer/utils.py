from mimetypes import guess_type
from urllib.parse import urlparse

from skimmer.exceptions import InvalidCropParametersError


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
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])


def validate_crop_parameters(
    left: int, top: int, right: int, bottom: int, ms: int
) -> None:
    """
    Validate crop box coordinates and timestamp before any fetch is attempted.

    Args:
        left (int): The left coordinate of the crop box.
        top (int): The top coordinate of the crop box.
        right (int): The right coordinate of the crop box.
        bottom (int): The bottom coordinate of the crop box.
        ms (int): The timestamp into the video in milliseconds.

    Raises:
        InvalidCropParametersError: If any parameter is out of range or inconsistent.
    """
    if left < 0 or top < 0 or right < 0 or bottom < 0:
        raise InvalidCropParametersError(
            "Crop coordinates (left, top, right, bottom) must be non-negative, "
            f"got left={left}, top={top}, right={right}, bottom={bottom}"
        )
    if right <= left:
        raise InvalidCropParametersError(
            f"right ({right}) must be greater than left ({left})"
        )
    if bottom <= top:
        raise InvalidCropParametersError(
            f"bottom ({bottom}) must be greater than top ({top})"
        )
    if ms < 0:
        raise InvalidCropParametersError(
            f"ms must be non-negative, got {ms}"
        )
