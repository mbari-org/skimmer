from sys import version as python_version

from flask import Flask, request
from psutil import cpu_count, virtual_memory

from skimmer.api.errors import describe_error
from skimmer.cache import CachedImage
from skimmer.core import Skimmer
from skimmer.config import THUMBNAIL_DEFAULT_SIZE
from skimmer.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from skimmer.exceptions import (
    InvalidCropParametersError,
    InvalidThumbnailParametersError,
)
from skimmer.api.flask.responses import ErrorResponse, ImageResponse, JSONResponse


def _image_response(image: CachedImage) -> ImageResponse:
    """Build an image response carrying the cached image's headers."""
    response = ImageResponse(image.get_data(), media_type=image.media_type)
    for header_name, header_value in image.headers.items():
        response.headers[header_name] = header_value
    return response


def _error_response(e: Exception) -> ErrorResponse:
    message, status, headers = describe_error(e)
    response = ErrorResponse(message, status=status)
    for header_name, header_value in headers.items():
        response.headers[header_name] = header_value
    return response


class SkimmerFlaskAPI:
    def __init__(self, skimmer: Skimmer):
        """
        Initialize the SkimmerFlaskAPI.

        Args:
            skimmer (Skimmer): The Skimmer instance.
        """
        self._skimmer = skimmer
        self._app = Flask(APP_NAME)
        self._configure()

    def crop(self) -> ImageResponse:
        """
        Crop the image based on the provided URL and coordinates.

        Returns:
            ImageResponse: The cropped image with custom headers.
        """
        url = request.args.get("url")
        try:
            try:
                left = int(request.args.get("left"))
                top = int(request.args.get("top"))
                right = int(request.args.get("right"))
                bottom = int(request.args.get("bottom"))
                ms = int(request.args.get("ms", 0))
            except (TypeError, ValueError):
                raise InvalidCropParametersError(
                    "left, top, right, bottom, and ms must be provided as integers"
                )

            cropped_image = self._skimmer.generate_crop(
                url, left, top, right, bottom, ms=ms
            )
            return _image_response(cropped_image)

        except Exception as e:
            return _error_response(e)

    def thumbnail(self) -> ImageResponse:
        """
        Generate a JPEG thumbnail of the image or video frame at the provided URL.

        Returns:
            ImageResponse: The JPEG thumbnail with custom headers.
        """
        url = request.args.get("url")
        size = request.args.get("size", THUMBNAIL_DEFAULT_SIZE)
        try:
            try:
                ms = int(request.args.get("ms", 0))
            except (TypeError, ValueError):
                raise InvalidThumbnailParametersError("ms must be an integer")

            thumbnail = self._skimmer.generate_thumbnail(url, size=size, ms=ms)
            return _image_response(thumbnail)

        except Exception as e:
            return _error_response(e)

    def health(self) -> JSONResponse:
        """
        Check the health of the API.

        Returns:
            JSONResponse: The health status of the API.
        """
        memory_info = virtual_memory()
        health_data = {
            "jdkVersion": f"Python {python_version}",
            "availableProcessors": cpu_count(),
            "freeMemory": memory_info.available,
            "maxMemory": memory_info.total,
            "totalMemory": memory_info.total,
            "application": APP_NAME,
            "version": APP_VERSION,
            "description": APP_DESCRIPTION,
        }

        return JSONResponse(health_data)

    def _configure(self) -> None:
        """
        Configure the Flask application routes.
        """
        self._app.route("/crop", methods=["GET"])(self.crop)
        self._app.route("/thumbnail", methods=["GET"])(self.thumbnail)
        self._app.route("/health", methods=["GET"])(self.health)

    @property
    def app(self) -> Flask:
        """
        Get the Flask application instance.

        Returns:
            Flask: The Flask application instance.
        """
        return self._app
