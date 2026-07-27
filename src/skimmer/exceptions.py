class InvalidURLError(Exception):
    """
    Exception raised for invalid URLs.
    """

    pass


class BeholderNotConfiguredError(Exception):
    """
    Exception raised when Beholder client is not configured.
    """

    pass


class InvalidCropParametersError(Exception):
    """
    Exception raised for invalid crop parameters (coordinates or timestamp).
    """

    pass


__all__ = [
    "InvalidURLError",
    "BeholderNotConfiguredError",
    "InvalidCropParametersError",
]
