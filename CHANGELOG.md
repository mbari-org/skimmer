# CHANGELOG


## v0.2.0 (2025-02-21)

### Chores

- Add pre-commit as a development dependency
  ([`ccb1ca2`](https://github.com/mbari-org/skimmer/commit/ccb1ca2789ceef9f0bb75a7b9a6775e654067e6c))

- Add pre-commit configuration for ruff linting and formatting
  ([`fa490f9`](https://github.com/mbari-org/skimmer/commit/fa490f92f80ff69d886506d53a2900221025d5ac))

- Update Dockerfile and environment configurations
  ([`3eaafeb`](https://github.com/mbari-org/skimmer/commit/3eaafebf31cd03e2c7fbb18c8c61002ca3efccab))

### Code Style

- Apply pre-commit hook
  ([`5b5640c`](https://github.com/mbari-org/skimmer/commit/5b5640c231b0c18d532d6620074938173c8acfd7))

### Documentation

- Update README to include Beholder integration and Docker Hub information
  ([`65f84c1`](https://github.com/mbari-org/skimmer/commit/65f84c13affb7198ddb5efba147abc0020fa549d))

- Update README with badges and author information
  ([`024a151`](https://github.com/mbari-org/skimmer/commit/024a151f606bf904e022b232908dd9ffc7a3473b))

### Features

- Add support for FastAPI and uvicorn
  ([`ea577ec`](https://github.com/mbari-org/skimmer/commit/ea577ec17c24192fa94083a3ee4b5e282eb200a7))

### Testing

- Switch from requests to httpx for mocking HTTP calls
  ([`03ff2d0`](https://github.com/mbari-org/skimmer/commit/03ff2d01cee612ad8ea6d15281f78f927d8106f7))


## v0.1.1 (2025-02-19)

### Bug Fixes

- Broaden Python availability, fix CI
  ([`b4935b2`](https://github.com/mbari-org/skimmer/commit/b4935b2a8b087c4401964347358eaee293b32bed))

### Chores

- Activate env before running pytest
  ([`cd7967d`](https://github.com/mbari-org/skimmer/commit/cd7967dd4a1dd7241af42b5532692a83609f5379))

- Fix CI order, create venv
  ([`de0b561`](https://github.com/mbari-org/skimmer/commit/de0b5614def436f846b9bfc3aa219f4e6edc54e0))

- Fix typo in python install in CI
  ([`83e4cb8`](https://github.com/mbari-org/skimmer/commit/83e4cb8d6c5d9ccb0109301a59399db2cbf05e8d))


## v0.1.0 (2025-02-19)

### Bug Fixes

- Fix create_app usage in gunicorn commands
  ([`bc24030`](https://github.com/mbari-org/skimmer/commit/bc24030dbe3debdc3df68ae7a9398498ae7bf2ad))

- Patch memory leak
  ([`205a9ea`](https://github.com/mbari-org/skimmer/commit/205a9ea7dfbffbff7053a668aaae3a4b8bc4bdf1))

- Remove debug print
  ([`9f113a4`](https://github.com/mbari-org/skimmer/commit/9f113a4d2be179b50dd9a3d1910517ff7722ee0f))

- Standardize ROI cache size to match image cache size
  ([`bce48a9`](https://github.com/mbari-org/skimmer/commit/bce48a91532151bfa7a4de67de8422336dffcba7))

### Chores

- Fix CI
  ([`4bb8eae`](https://github.com/mbari-org/skimmer/commit/4bb8eae4dc79dfac0d50de5ac0908fcf3c709f9a))

- Move Docker-related files to docker dir, add build/push scripts
  ([`0686722`](https://github.com/mbari-org/skimmer/commit/068672297ea769c96dc967ff82ac1e4e147ee9da))

- Reduce IMAGE_CACHE_SIZE_MB in example Docker Compose configuration
  ([`cce467b`](https://github.com/mbari-org/skimmer/commit/cce467ba5497d9ab367bbb3d97a7fb2d5e7d6808))

### Code Style

- Format
  ([`4ebaa14`](https://github.com/mbari-org/skimmer/commit/4ebaa140cd595cb89e38cdd0bd903bb20bb4d847))

- Update project name capitalization in README
  ([`52dd71d`](https://github.com/mbari-org/skimmer/commit/52dd71d4066fe10024409fd73a96d5b0b52016c8))

### Documentation

- Add copyright notice to README
  ([`5bc8089`](https://github.com/mbari-org/skimmer/commit/5bc8089bbe65e3b5300c5f0e440c709aec32944b))

- Add gear emoji to Environment Variables section
  ([`72c730b`](https://github.com/mbari-org/skimmer/commit/72c730b5ecf2cb03a7fec72ffa23a8fc86551b44))

- Add LICENSE file with MIT license terms
  ([`aa6ee31`](https://github.com/mbari-org/skimmer/commit/aa6ee314ef108b945bf13ca216c6fbe2ce37c9d4))

- Update README to include persistent volume instructions for Docker container
  ([`5fcfc74`](https://github.com/mbari-org/skimmer/commit/5fcfc745c01bba886857452ed231ebed5a8ce1e9))

- Update README to include usage instructions and health check endpoint
  ([`5a444e8`](https://github.com/mbari-org/skimmer/commit/5a444e8d86b71a2b423907f28cff5aba3839dd4a))

- Update README to refine project description and improve clarity
  ([`1a7568e`](https://github.com/mbari-org/skimmer/commit/1a7568ecaa98adc8bdda67bd92dcfa29ec958527))

- Update README with Docker Compose instructions and environment variables
  ([`6fdfe1a`](https://github.com/mbari-org/skimmer/commit/6fdfe1ac65c97b84bf000c313e51b2de0c7c2778))

### Features

- Add gunicorn configuration and update Dockerfile to include it
  ([`6bdb0b4`](https://github.com/mbari-org/skimmer/commit/6bdb0b4a82b8808314946462b6340d3c026db184))

- Add health check endpoint and application constants
  ([`9b1a765`](https://github.com/mbari-org/skimmer/commit/9b1a76533031b15823662505db5839715f728883))

- Implement gunicorn
  ([`919f0c3`](https://github.com/mbari-org/skimmer/commit/919f0c398716df354f61e36513f65db76b4fab0f))

- Init skimmer project with core functionality, configuration, and Docker support
  ([`6477601`](https://github.com/mbari-org/skimmer/commit/6477601f9e4f6f0d2a7b140c58dc70182a4ca54e))

- Integrate Beholder client for video frame extraction and update image fetching logic
  ([`0c96427`](https://github.com/mbari-org/skimmer/commit/0c96427045de6315c5f788dee684211ae86944d8))

- Remove hacky beholder custom protocol, major refactor
  ([`dba072b`](https://github.com/mbari-org/skimmer/commit/dba072b005d2bdfd8c6fc283cfbbffa749341b58))

- Update caching mechanism to cache full images in memory, swap out to diskcache for rois
  ([`c29dc3f`](https://github.com/mbari-org/skimmer/commit/c29dc3f02b06d396afe65839b94d9b8aa8f37cbb))

- Update compose.yaml to configure application workers
  ([`b882c32`](https://github.com/mbari-org/skimmer/commit/b882c32df1c68c99c12885e9c238e426568e512a))

### Testing

- Add environment configuration for testing and update cache eviction test logic
  ([`469c9a9`](https://github.com/mbari-org/skimmer/commit/469c9a90edb70d55231542109d1a4a84e9dff46e))
