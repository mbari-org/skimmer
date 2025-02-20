from io import BytesIO

from flask import Flask, request, send_file, Response
from psutil import cpu_count, virtual_memory
from sys import version as python_version

from skimmer.core import Skimmer
from skimmer.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from skimmer.exceptions import InvalidURLError, BeholderNotConfiguredError
from skimmer.responses import ErrorResponse, JSONResponse
from skimmer.utils import is_valid_url


class SkimmerAPI:
    def __init__(self, skimmer: Skimmer):
        """
        Initialize the SkimmerAPI.

        Args:
            skimmer (Skimmer): The Skimmer instance.
        """
        self._skimmer = skimmer
        self._app = Flask(APP_NAME)
        self._configure()

    def crop(self) -> Response:
        """
        Crop the image based on the provided URL and coordinates.

        Returns:
            Response: The cropped image with custom headers.
        """
        url = request.args.get("url")
        try:
            if not is_valid_url(url):
                raise InvalidURLError(f"Invalid URL: {url}")

            left = int(request.args.get("left"))
            top = int(request.args.get("top"))
            right = int(request.args.get("right"))
            bottom = int(request.args.get("bottom"))
            ms = int(request.args.get("ms", 0))

            cropped_image = self._skimmer.generate_crop(
                url, left, top, right, bottom, ms=ms
            )
            response = send_file(
                BytesIO(cropped_image.get_data()), mimetype="image/png"
            )
            response.headers["X-Cache"] = cropped_image.headers["X-Cache"]
            return response

        except InvalidURLError as e:
            return ErrorResponse(str(e))
        except BeholderNotConfiguredError as e:
            return ErrorResponse(str(e), status=500)
        except Exception as e:
            return ErrorResponse(f"An unexpected error occurred: {str(e)}", status=500)

    def health(self) -> Response:
        """
        Check the health of the API.

        Returns:
            Response: The health status of the API.
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
