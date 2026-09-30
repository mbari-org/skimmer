"""Framework-agnostic mapping of Skimmer exceptions to HTTP error responses.

Shared by the Flask and FastAPI layers so both report errors identically.
"""

import random

import httpx

from skimmer.backpressure import Saturated, StaleWork
from skimmer.exceptions import (
    BeholderNotConfiguredError,
    InvalidCropParametersError,
    InvalidThumbnailParametersError,
    InvalidURLError,
)


def retry_after_seconds() -> float:
    """Jittered so clients shed by the same burst don't all retry in the same instant."""
    return round(random.uniform(1.0, 3.0), 1)


def describe_error(e: Exception) -> tuple[str, int, dict[str, str]]:
    """
    Map an exception raised while serving an image to an HTTP error.

    Args:
        e (Exception): The exception raised.

    Returns:
        tuple[str, int, dict[str, str]]: The error message, status code, and extra headers.
    """
    if isinstance(
        e,
        (InvalidURLError, InvalidCropParametersError, InvalidThumbnailParametersError),
    ):
        return str(e), 400, {}
    if isinstance(e, BeholderNotConfiguredError):
        return str(e), 500, {}
    if isinstance(e, Saturated):
        return (
            "The server is at capacity. Please retry shortly.",
            503,
            {"Retry-After": str(retry_after_seconds())},
        )
    if isinstance(e, StaleWork):
        return (
            "Your request waited too long to start. Please retry shortly.",
            503,
            {"Retry-After": str(retry_after_seconds())},
        )
    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 503:
        return (
            "Beholder is at capture capacity. Please retry shortly.",
            503,
            {
                "Retry-After": e.response.headers.get(
                    "Retry-After", str(retry_after_seconds())
                )
            },
        )
    return f"An unexpected error occurred: {str(e)}", 500, {}


__all__ = ["describe_error", "retry_after_seconds"]
