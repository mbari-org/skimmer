import shutil

import pytest
from dotenv import load_dotenv

load_dotenv("env/.env.test", override=True)

# Imported after load_dotenv so config picks up the test environment
from skimmer import Skimmer, create_default_flask_app  # noqa: E402
from skimmer.config import CACHE_DIR  # noqa: E402


@pytest.fixture
def client():
    app = create_default_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_cache():
    Skimmer()._cache.clear()
    shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
