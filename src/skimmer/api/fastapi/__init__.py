from sys import version as python_version

from fastapi import FastAPI
from psutil import cpu_count, virtual_memory

from skimmer.api.errors import describe_error
from skimmer.api.fastapi.models import Error, HealthStatus
from skimmer.cache import CachedImage
from skimmer.core import Skimmer
from skimmer.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from skimmer.api.fastapi.responses import ErrorResponse, ImageResponse, JSONResponse


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


class SkimmerFastAPI:
    def __init__(self, skimmer: Skimmer):
        """
        Initialize the SkimmerFastAPI.

        Args:
            skimmer (Skimmer): The Skimmer instance.
        """
        self._skimmer = skimmer
        self._app = FastAPI()
        self._configure()

    async def crop(
        self,
        url: str,
        left: int,
        top: int,
        right: int,
        bottom: int,
        ms: int = 0,
    ) -> ImageResponse:
        """
        Crop the image based on the provided URL and coordinates.
        """
        try:
            cropped_image = await self._skimmer.generate_crop_async(
                url, left, top, right, bottom, ms=ms
            )
            return _image_response(cropped_image)

        except Exception as e:
            return _error_response(e)

    async def health(self) -> JSONResponse:
        """
        Check the health of the API.
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
        Configure the FastAPI application.
        """
        self._app.add_api_route(
            "/crop",
            self.crop,
            methods=["GET"],
            status_code=200,
            responses={
                200: {"content": {"image/png": {}}},
                400: {"model": Error},
                500: {"model": Error},
            },
            response_class=ImageResponse,
        )
        self._app.add_api_route(
            "/health", self.health, methods=["GET"], response_model=HealthStatus
        )

    @property
    def app(self) -> FastAPI:
        """
        Get the FastAPI application instance.

        Returns:
            FastAPI: The FastAPI application instance.
        """
        return self._app
