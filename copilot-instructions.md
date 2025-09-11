# Skimmer ROI Cropping Service

Skimmer is a Python service that fetches images from URLs, crops them based on bounding box coordinates, caches results, and returns cropped images. It integrates with Beholder for video frame extraction and provides both Flask (WSGI) and FastAPI (ASGI) implementations.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Dependencies
- Install uv package manager (if not available):
  ```bash
  pip install uv
  ```
- Build the package:
  ```bash
  uv build  # Takes 0.5 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
  ```
- Create virtual environment:
  ```bash
  uv venv --python 3.12  # Takes 0.01 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
  ```
- Install package with dependencies:
  ```bash
  uv pip install .  # Takes 0.3-3 seconds (faster after first install). NEVER CANCEL. Set timeout to 60+ seconds.
  ```

### Testing
- Run the complete test suite:
  ```bash
  source .venv/bin/activate
  pytest -v  # Takes 1-2 seconds, runs 9 tests. NEVER CANCEL. Set timeout to 60+ seconds.
  ```
- For specific test output: `pytest -v tests/test_skimmer.py`
- Tests use `.env.test` configuration automatically via conftest.py

### Development Server Startup
- Set up environment configuration:
  ```bash
  cp env/.env.example .env  # Edit as needed for your environment
  ```

#### Flask Server (Gunicorn WSGI)
- Start Flask development server:
  ```bash
  source .venv/bin/activate
  ./run_flask.sh  # Takes 3-5 seconds to start. NEVER CANCEL. Set timeout to 60+ seconds.
  ```
- Runs on http://localhost:5000 by default

#### FastAPI Server (Uvicorn ASGI)  
- Start FastAPI development server:
  ```bash
  source .venv/bin/activate
  ./run_fastapi.sh  # Takes 3-5 seconds to start. NEVER CANCEL. Set timeout to 60+ seconds.
  ```
- Runs on http://localhost:5000 by default

### Linting and Formatting
- Install ruff if not available: `pip install ruff`
- Check code style:
  ```bash
  ruff check .  # Takes 0.01 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
  ```
- Format code:
  ```bash
  ruff format .  # Takes 0.01 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
  ```
- Check formatting without changes:
  ```bash
  ruff format --check .
  ```

### Pre-commit Hooks
- Install pre-commit: `pip install pre-commit`
- Install hooks:
  ```bash
  pre-commit install  # Takes 0.1 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
  ```
- Run hooks manually: `pre-commit run --all-files`

## Validation

### Manual Validation Requirements
- **CRITICAL**: Always test the health endpoint after starting either server:
  ```bash
  curl -s http://localhost:5000/health
  ```
- Expected response: JSON with system info including Python version, memory stats, and application details
- **ALWAYS** verify the server responds correctly before proceeding with development

### Validation Scenarios
- **Health Check**: Run `curl http://localhost:5000/health` and verify JSON response with system information
- **Server Startup**: Both Flask and FastAPI servers should start within 5 seconds and respond to health checks
- **Test Suite**: All 9 tests should pass in under 3 seconds
- **Linting**: Both `ruff check` and `ruff format --check` should complete cleanly in under 0.1 seconds

### CI Pipeline Validation
- Always run before committing:
  ```bash
  uv build && source .venv/bin/activate && pytest -v && ruff check . && ruff format --check .
  ```
- Total time: Under 2 seconds for complete validation cycle

## Network Limitations
- **IMPORTANT**: External network access may be limited in some environments
- If image fetching from external URLs fails with "No address associated with hostname", this is expected
- Tests use mocked HTTP responses and will work regardless of network connectivity
- The `/crop` endpoint functionality can be tested with local test images when network is available

## Docker Support
- Multi-stage Dockerfile available in `docker/Dockerfile`
- Build script: `docker/build.sh` (requires Docker buildx for multi-platform)
- Compose configuration: `docker/compose.yaml`
- Default Docker image runs Flask with gunicorn

## Common Tasks

### Repository Structure
```
.
├── .github/
│   └── workflows/ci.yaml          # CI pipeline with build, test, release
├── docker/
│   ├── Dockerfile                 # Multi-stage Docker build
│   ├── build.sh                  # Docker build script
│   └── compose.yaml              # Docker Compose configuration
├── env/
│   ├── .env.example              # Environment variable template
│   ├── .env.test                 # Test environment config
│   └── gunicorn.conf.py          # Gunicorn configuration
├── src/skimmer/
│   ├── __init__.py               # Main app factories
│   ├── api/                      # Flask and FastAPI implementations
│   ├── core.py                   # Core Skimmer class
│   ├── cache.py                  # Caching logic
│   ├── config.py                 # Configuration management
│   └── constants.py              # App constants
├── tests/
│   ├── conftest.py               # Test configuration
│   ├── test_skimmer.py           # Main test suite
│   └── test_image.png            # Test image file
├── pyproject.toml                # Project configuration and dependencies
├── run_flask.sh                  # Flask startup script
├── run_fastapi.sh               # FastAPI startup script
└── README.md                     # Project documentation
```

### Key Files to Monitor
- When changing API contracts, always check both `src/skimmer/api/flask/` and `src/skimmer/api/fastapi/`
- Configuration changes affect `src/skimmer/config.py`
- Core image processing logic in `src/skimmer/core.py`
- Cache implementation in `src/skimmer/cache.py`

### Environment Variables
Key environment variables (see `env/.env.example`):
- `IMAGE_CACHE_SIZE_MB`: In-memory cache size (default: 100)
- `ROI_CACHE_SIZE_MB`: Filesystem cache size (default: 100) 
- `CACHE_DIR`: Cache directory (default: /tmp/skimmer_cache)
- `APP_HOST`: Server host (default: 0.0.0.0)
- `APP_PORT`: Server port (default: 5000)
- `APP_WORKERS`: Number of workers (default: 1)
- `BEHOLDER_URL`: Beholder service URL for video processing
- `BEHOLDER_API_KEY`: API key for Beholder authentication

### API Endpoints
- `GET /health`: Health check endpoint returning system information
- `GET /crop`: Main cropping endpoint with query parameters:
  - `url`: Image or video URL
  - `left`, `top`, `right`, `bottom`: Bounding box coordinates  
  - `ms`: Timestamp for video frames (optional)

### Performance Notes
- **Build time**: 0.5 seconds
- **Virtual environment creation**: 0.01 seconds  
- **Dependency installation**: 0.3 seconds (after first install, from cache)
- **Test suite**: 2 seconds (9 tests pass)
- **Server startup**: 3-5 seconds
- **Linting (ruff check)**: 0.01 seconds
- **Formatting check (ruff format --check)**: 0.01 seconds
- **Pre-commit hook installation**: 0.1 seconds
- **Complete CI validation cycle**: Under 2 seconds (build + test + lint + format)
- **Total development cycle**: Under 10 seconds from clean build to running server

### Dependencies
- **Python**: 3.12+ required (specified in .python-version)
- **Package manager**: uv (modern Python package manager)
- **Key libraries**: Pillow, httpx, Flask, FastAPI, cachetools, pytest
- **Build system**: hatchling
- **Linting**: ruff (replaces black, flake8, isort)
