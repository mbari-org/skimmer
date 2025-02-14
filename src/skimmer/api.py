from io import BytesIO

from flask import Flask, request, send_file, Response

from skimmer.core import Skimmer
from skimmer.constants import APP_NAME
from skimmer.exceptions import InvalidURLError, BeholderNotConfiguredError
from skimmer.responses import ErrorResponse
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

    def _configure(self) -> None:
        """
        Configure the Flask application routes.
        """
        self._app.route("/crop", methods=["GET"])(self.crop)

    @property
    def app(self) -> Flask:
        """
        Get the Flask application instance.

        Returns:
            Flask: The Flask application instance.
        """
        return self._app
