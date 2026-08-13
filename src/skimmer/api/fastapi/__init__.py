import random
from sys import version as python_version

import httpx
from fastapi import FastAPI
from psutil import cpu_count, virtual_memory

from skimmer.api.fastapi.models import Error, HealthStatus
from skimmer.backpressure import Saturated, StaleWork
from skimmer.core import Skimmer
from skimmer.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from skimmer.exceptions import (
    InvalidURLError,
    BeholderNotConfiguredError,
    InvalidCropParametersError,
)
from skimmer.api.fastapi.responses import ErrorResponse, ImageResponse, JSONResponse


def _retry_after_seconds() -> float:
    """Jittered so clients shed by the same burst don't all retry in the same instant."""
    return round(random.uniform(1.0, 3.0), 1)


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
