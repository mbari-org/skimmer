from flask import Flask

from skimmer.core import Skimmer
from skimmer.api import SkimmerAPI


def create_default_flask_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application.
    """
    skimmer = Skimmer()
    skimmer_api = SkimmerAPI(skimmer)
    return skimmer_api.app


__all__ = [
    "Skimmer",
    "SkimmerAPI",
    "create_default_flask_app",
]
