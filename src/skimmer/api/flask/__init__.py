import random
from sys import version as python_version

import httpx
from flask import Flask, request
from psutil import cpu_count, virtual_memory

from skimmer.backpressure import Saturated, StaleWork
from skimmer.core import Skimmer
from skimmer.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from skimmer.exceptions import (
    InvalidURLError,
    BeholderNotConfiguredError,
    InvalidCropParametersError,
)
from skimmer.api.flask.responses import ErrorResponse, ImageResponse, JSONResponse


def _retry_after_seconds() -> float:
    """Jittered so clients shed by the same burst don't all retry in the same instant."""
    return round(random.uniform(1.0, 3.0), 1)


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
            response = ImageResponse(cropped_image.get_data())
            # Copy all headers from the cached ROI
            for header_name, header_value in cropped_image.headers.items():
                response.headers[header_name] = header_value
            return response

        except (InvalidURLError, InvalidCropParametersError) as e:
            return ErrorResponse(str(e))
        except BeholderNotConfiguredError as e:
            return ErrorResponse(str(e), status=500)
        except Saturated:
            response = ErrorResponse(
                "The server is at crop capacity. Please retry shortly.", status=503
            )
            response.headers["Retry-After"] = str(_retry_after_seconds())
            return response
        except StaleWork:
            response = ErrorResponse(
                "Your request waited too long to start. Please retry shortly.", status=503
            )
            response.headers["Retry-After"] = str(_retry_after_seconds())
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                response = ErrorResponse(
                    "Beholder is at capture capacity. Please retry shortly.", status=503
                )
                response.headers["Retry-After"] = e.response.headers.get(
                    "Retry-After", str(_retry_after_seconds())
                )
                return response
            return ErrorResponse(f"An unexpected error occurred: {str(e)}", status=500)
        except Exception as e:
            return ErrorResponse(f"An unexpected error occurred: {str(e)}", status=500)

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
        self._app.route("/health", methods=["GET"])(self.health)

    @property
    def app(self) -> Flask:
        """
        Get the Flask application instance.

        Returns:
            Flask: The Flask application instance.
        """
        return self._app
