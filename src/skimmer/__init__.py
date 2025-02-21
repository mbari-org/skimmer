from fastapi import FastAPI
from flask import Flask

from skimmer.core import Skimmer
from skimmer.api import SkimmerFlaskAPI, SkimmerFastAPI


def create_default_flask_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application.
    """
    skimmer = Skimmer()
    skimmer_api = SkimmerFlaskAPI(skimmer)
    return skimmer_api.app


def create_default_fastapi_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured FastAPI application.
    """
    skimmer = Skimmer()
    skimmer_api = SkimmerFastAPI(skimmer)
    return skimmer_api.app


__all__ = [
    "Skimmer",
    "SkimmerFlaskAPI",
    "create_default_flask_app",
    "create_default_fastapi_app",
]
