# CHANGELOG


## v0.4.0 (2026-07-27)

### Bug Fixes

- Return captured frame from fetch_video_frame_async
  ([`c84318a`](https://github.com/mbari-org/skimmer/commit/c84318a6d5b392243dc26cfc9d4fd8686919bc34))

fetch_video_frame_async cached the Beholder-captured frame but never returned it, so
  generate_crop_async would call .crop() on None for any async-path video request. Return the image,
  matching the sync fetch_video_frame twin.

### Features

- Pre-validate crop parameters before fetching image/video frames
  ([`7d81702`](https://github.com/mbari-org/skimmer/commit/7d817025d8a8ce7915d4cf34e9a009509b1cbed8))

Validate the URL and crop coordinates (non-negative, right>left, bottom>top, ms>=0) up front in
  Skimmer.generate_crop/_async, before any cache lookup or network/frame fetch, and surface bad
  input as a descriptive 400 via InvalidCropParametersError in both the FastAPI and Flask handlers.

### Performance Improvements

- Use threaded gunicorn workers and a pooled HTTP client under load
  ([`068bb07`](https://github.com/mbari-org/skimmer/commit/068bb075eeb8c84cc355e242567b55d574151c7d))

Sync gunicorn workers handled one request at a time each, capping concurrency at APP_WORKERS
  regardless of how I/O-bound a request is (upstream fetch, disk cache). Switch to gthread workers
  with a tunable APP_THREADS so each worker can overlap I/O waits across threads.

Since the in-memory image LRUCache isn't thread-safe, guard it with a lock now that concurrent
  access within a worker is possible.

Also reuse a single httpx.Client (with explicit timeouts) across sync image fetches instead of
  opening a new connection per request, and add a timeout to the async fetch path.


## v0.3.2 (2026-07-15)

### Bug Fixes

- Disable SSL verification for image fetch requests
  ([`f829361`](https://github.com/mbari-org/skimmer/commit/f8293611eb4ecb99fe34c6df0200ecca44984cc6))

- Evict ROI cache entries by least-recently-used instead of insertion order
  ([`5dc05d1`](https://github.com/mbari-org/skimmer/commit/5dc05d1224e9e26b2e82dfe9d11aff5a820eced2))

The disk cache defaulted to diskcache's least-recently-stored policy, which evicts by insertion time
  regardless of access frequency. This let frequently-requested crops get evicted in favor of stale,
  rarely-used entries once the cache hit its size limit.

### Testing

- Expect verify=False in redirect test assertions
  ([`0a2b451`](https://github.com/mbari-org/skimmer/commit/0a2b451ab0db3de445c270621303ca980d24e45a))

fetch_image now calls httpx.get with verify=False, so the mocked-call assertions in the redirect
  tests need updating to match.

- Fix cache eviction test touching LRU recency in its own loop condition
  ([`93990f9`](https://github.com/mbari-org/skimmer/commit/93990f9d857e2f945a14dd248ce150fd71616637))

Checking membership via .get() bumps access_time under the least-recently-used eviction policy, so
  the loop's own termination check kept the target key perpetually "recently used" and prevented it
  from ever being evicted. Use `in` for a non-touching existence check instead.


## v0.3.1 (2026-01-12)

### Bug Fixes

- Fix 307 response causing 500 error ([#9](https://github.com/mbari-org/skimmer/pull/9),
  [`dce3249`](https://github.com/mbari-org/skimmer/commit/dce32498ad39254924468debb861951d5d099121))

### Chores

- Add dev group in CI deps install
  ([`a5a6eca`](https://github.com/mbari-org/skimmer/commit/a5a6eca600a02ef8ad6f0a13b13e257dcb024f4a))


## v0.3.0 (2025-09-11)

### Chores

- Minimize Docker image size
  ([`aa07c77`](https://github.com/mbari-org/skimmer/commit/aa07c77d1c5e18cac62e3bcc3360dd001288bfa2))

- Update default gunicorn conf to disable access log to stdout
  ([`2b8a5fa`](https://github.com/mbari-org/skimmer/commit/2b8a5fab3060cfed3ef80d5cb9fd18122f0191b8))

- Update Dockerfile to copy gunicorn configuration from env directory
  ([`9f7e706`](https://github.com/mbari-org/skimmer/commit/9f7e7063cc71498268db864173bca7a768dffe30))

- Use docker buildx for multi-platform builds
  ([`08802a4`](https://github.com/mbari-org/skimmer/commit/08802a4b5a22e667332294479a8611948d1d3752))

### Documentation

- Add instructions for Copilot
  ([`6063ac9`](https://github.com/mbari-org/skimmer/commit/6063ac9ba62d4aea7098e3f1d28fb0d28eede10b))

### Features

- Add client-side caching headers for browser and CDN optimization
  ([#5](https://github.com/mbari-org/skimmer/pull/5),
  [`007b085`](https://github.com/mbari-org/skimmer/commit/007b0853dfb63def614216ac7e7dcfa23d2eb1a3))

* Initial plan

* Add client-side caching headers (Cache-Control and ETag)

Co-authored-by: kevinsbarnard <40082734+kevinsbarnard@users.noreply.github.com>

---------

Co-authored-by: copilot-swe-agent[bot] <198982749+Copilot@users.noreply.github.com>


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
