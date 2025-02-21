from json import dumps

from flask import Response


class ImageResponse(Response):
    """
    A custom image response class.

    Args:
        image (bytes): The image byte data.
        status (int): The HTTP status code. Defaults to 200.
    """

    def __init__(self, response: bytes, status: int = 200):
        super().__init__(response, status=status, mimetype="image/png")


class JSONResponse(Response):
    """
    A custom JSON response class.

    Args:
        response (dict): The response data.
        status (int): The HTTP status code. Defaults to 200.
    """

    def __init__(self, response: dict, status: int = 200):
        super().__init__(dumps(response), status=status, mimetype="application/json")


class ErrorResponse(JSONResponse):
    """
    A custom error response class.

    Args:
        message (str): The error message.
        status (int): The HTTP status code. Defaults to 400.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__({"error": message}, status=status)
