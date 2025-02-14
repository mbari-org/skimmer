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


__all__ = [
    "InvalidURLError",
    "BeholderNotConfiguredError",
]
