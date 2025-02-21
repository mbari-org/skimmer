from io import BytesIO
from fastapi.responses import JSONResponse as FastAPIJSONResponse, StreamingResponse


class ImageResponse(StreamingResponse):
    """
    A custom image response class.

    Args:
        image (bytes): The image byte data.
        status (int): The HTTP status code. Defaults to 200.
    """

    def __init__(self, response: bytes, status: int = 200):
        super().__init__(BytesIO(response), media_type="image/png", status_code=status)


class JSONResponse(FastAPIJSONResponse):
    """
    A custom JSON response class.

    Args:
        response (dict): The response data.
        status (int): The HTTP status code. Defaults to 200.
    """

    def __init__(self, response: dict, status: int = 200):
        super().__init__(response, status_code=status)


class ErrorResponse(JSONResponse):
    """
    A custom error response class.

    Args:
        message (str): The error message.
        status (int): The HTTP status code. Defaults to 400.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__({"error": message}, status=status)
