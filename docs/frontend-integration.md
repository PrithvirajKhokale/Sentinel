# Full-data integration

## Public deployment (current)

The Render service runs with `SENTINEL_PUBLIC_ACCESS=true`: the read-only API needs
no token, CORS allows any origin (GET only, no credentials), `/docs` is enabled,
and `SENTINEL_FRONTEND_DIR` serves the dashboard from the same public URL. The
private ChatGPT Sites page is retired. Public mode refuses to start if
`SENTINEL_API_TOKEN` or `SENTINEL_ALLOWED_ORIGINS` is also set, so token mode
remains available by removing `SENTINEL_PUBLIC_ACCESS`. The sections below record
the earlier authenticated/private setup.

The repository now includes the React + Vite frontend, unchanged source-preserving
API contract, persistent dark-mode preference, local same-origin development proxy,
optional same-origin static serving, and a Docker build for the Python API plus UI.

## Reproduce the validated data

1. Install requirements-backend.txt in a Python virtual environment.
2. Run `python scripts/acquire_reports.py` to recover the five exact government PDFs.
   Downloads must match the existing catalog hashes; changed bytes fail closed.
3. Run `python scripts/rebuild_dataset.py` to run all five extractions and history.
4. Start the documented local PostgreSQL instance; set DATABASE_URL.
5. Run `python -m alembic upgrade head` and `python -m backend.import_dataset`.

The original revision hashes include CRLF bytes for the code/catalog/references.
.gitattributes preserves those exact checked bytes on Linux and Windows. Do not
edit the manifest to work around a mismatch. Generated data and PDFs stay ignored.

## Local application

Run `python -m backend.serve`. In another terminal, enter frontend, run `npm ci`
then `npm run dev`. Vite proxies /api to the loopback backend. The default local UI
uses real API responses. A backend error never silently becomes sample data.
The Data connection dialog checks a candidate connection before applying it.

For one-process serving, build the frontend with VITE_API_BASE_URL=/api/v1, set
SENTINEL_FRONTEND_DIR to the absolute frontend/dist path, then start the backend.

## Authenticated hosting

The Dockerfile builds both components and serves them from one origin. It does not
bundle PDFs, database credentials, generated data, or browser-visible API tokens.
Build context excludes data and secrets. The image connects to the approved PostgreSQL database. Its build recovers the
exact reports and validates the revision; startup migrates and imports it before
serving requests.

Production environment:

- APP_ENV=production
- DATABASE_URL=postgresql+psycopg://... with explicit sslmode=require, verify-ca or
  verify-full (prefer verify-full with the provider's CA/certificate configuration)
- SENTINEL_API_TOKEN: a random secret of at least 32 ASCII characters without spaces
- API_HOST=0.0.0.0; PORT supplied by the hosting provider, or API_PORT=8000
- SENTINEL_FRONTEND_DIR=/app/frontend/dist (already set in the image)
- SENTINEL_ALLOWED_ORIGINS: comma-separated exact HTTPS origins, only when accessing
  the API from a separate frontend such as the existing private Sites URL

Use a provider that terminates HTTPS. The API requires the bearer token on every
/api route; schema/docs endpoints are disabled in production. The token is an
initial owner credential, not a multi-user account/role system. Enter it in the
Data connection dialog; it remains only in React memory. Never use a VITE_ variable
for secrets. The UI shell itself is not an authentication boundary: retain the
private Sites frontend or configure provider-level access for a co-hosted UI.
The public /healthz response is only liveness and does not certify dataset readiness.

## Verification

Run `python -m unittest discover -s tests -v` with BACKEND_TEST_DATABASE_URL for full
PostgreSQL checks; without it database checks explicitly skip. Run frontend's
`npm test` and build. `frontend/tests/live-api.mjs` exercises the real JavaScript
client against all four Python endpoints using the complete imported dataset.

## Hosting boundary

Sites hosts the existing private static interface; it does not directly run the
Python/PostgreSQL service. A durable Python host and PostgreSQL hosting account
must be supplied or connected to put the full-data API online. No paid service is
created, no local service is publicly tunneled, and no audience is changed by this
integration. Until that deployment exists, the current private URL remains in
reference-example mode. This document does not claim production deployment.

### Verification recorded on 2026-10-15

All five recovered PDF hashes and the full original manifest validated unchanged:
9,321 snapshots and 7,202 comparisons. The full import, SQL migrations and schema
check passed using a loopback PGlite PostgreSQL WASM development server. The real
JavaScript client passed HTTP checks against the authenticated Python API for
list/paging/search, raw/null/zero detail values, provenance, explicit history gaps,
portfolio counts, independent scope filters, and contract errors. The built UI
was served by the same Python process and unauthenticated data requests returned 401.

Python suite: 40 passed, 28 native PostgreSQL integration checks explicitly skipped.
Frontend suite: 10 passed; production frontend build and Python dependency check
passed. Native PostgreSQL regression tests, Docker image build and browser visual
QA remain to be run in an environment supporting them. PGlite verification is not
a claim that native PostgreSQL concurrency, production TLS or hosting was tested.


## Prepared Render configuration

render.yaml declares a free Docker API service in Singapore, wired to the
existing free sentinel-db in the approved workspace. The API serves no frontend files; the existing owner-private Sites
interface stays the entry point. Only /healthz is an unauthenticated liveness
endpoint. The API token is generated by Render and the exact private frontend
origin is allowed by CORS. PostgreSQL URLs generated by Render are translated to
the pinned psycopg driver, with explicit TLS configuration.

The Blueprint is configuration preparation, not deployment completion. The image recovers exact public PDFs and validates the original revision during
build. Startup runs Alembic and activates that revision before opening the API.
Subsequent restarts retain the active database revision. External DB
access defaults to denied (ipAllowList: []); perform import from a Render-side
job/shell or explicitly authorize an appropriately restricted temporary import
route. The source branch must exist remotely before the Blueprint can be applied.
Workspace selection and public repository publication were approved on 2026-10-15.
Free resources are a demo starting point; check current expiry, sleeping and
capacity limits in Render before relying on them for a persistent deployment.


## Reproducible source archive deployment (2026-10-17)

Render build previously failed in `scripts/acquire_reports.py` because the
government portal timed out. All five original user-supplied PDFs now match the
previously reviewed `config/monthly_reports.json` SHA-256 checksums byte-for-byte.
The upload bundle is `sentinel-source-reports-2026.zip` (25,893,567 bytes;
SHA-256 `a5da5970b6156935e93a20ef8a31e1aa16c5e805cbf21562ab27371c544f1680`).
It contains exactly these files at ZIP root:
`FlashReport_April2026.pdf`, `FlashReport_May2026.pdf`,
`FlashReport_June_2026.pdf`, `FlashReport_July_2026.pdf`,
`FlashReport_August_2026.pdf`.

**One-time prerequisite:** Using the GitHub Releases web UI, publish a release
tagged `source-reports-2026-v1` on this repository and upload that exact ZIP
as an asset named `sentinel-source-reports-2026.zip`. This must be publicly
reachable by Render; the repository is currently public. Do not put API tokens,
database credentials, or private records in the release.

The acquisition script downloads exactly this release asset once and verifies
the pinned archive SHA-256, the exact member-name set, every PDF signature, and
each catalog SHA-256 before placing the source files into `data/raw`.
Cached sources are verified without network. Source mismatches stop the build.
Extraction and dataset-manifest validation are unchanged.

Before triggering Render manually (auto deploy is disabled), confirm
the release URL serves the expected ZIP rather than a 404. Do not deploy before
that prerequisite, because a missing release would fail the build. After
deploying, check `/healthz`, dataset readiness, protected endpoints, the full
9,321/7,202 counts, and frontend CORS/auth integration. No deployment or
production tests are implied by this document.
