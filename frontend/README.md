# Sentinel React frontend

React 19 + Vite 7 dashboard for the Sentinel monitoring API (contract v1). In
production it is served publicly by the same Render service as the API.

## Getting started

Requires Node.js 22+.

```powershell
cd frontend
npm ci
npm run dev        # http://127.0.0.1:5173
```

`npm run dev` expects the backend on 127.0.0.1:8000 (see ../docs/backend-local.md);
Vite proxies `/api` to it. An unavailable API stays an error; switch explicitly to
**Reference examples** in the Data connection dialog to use the checked samples
in `public/reference-data.json`.

To use the deployed public API instead of a local backend, point the dev proxy at it:

```powershell
$env:SENTINEL_API_PROXY_TARGET = 'https://sentinel-api-waat.onrender.com'
npm run dev
```

The API is public and allows cross-origin requests, so the Data connection
dialog can also use `https://sentinel-api-waat.onrender.com/api/v1` directly.

| Script | Purpose |
|---|---|
| `npm run dev` | Development server with hot reload |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm test` | Contract/client unit tests (`tests/*.test.mjs`) |

## Project structure

```text
frontend/
├── index.html                 # HTML shell; applies saved theme before React loads
├── vite.config.js             # React plugin, dev server and /api proxy
├── .env.example               # VITE_API_BASE_URL (never put secrets in VITE_ vars)
├── public/
│   └── reference-data.json    # Checked reference examples (offline mode)
├── src/
│   ├── main.jsx               # Entry point: mounts <App />
│   ├── App.jsx                # Layout, page switching, shared state
│   ├── constants.js           # Report months, identity fields, field labels
│   ├── api/
│   │   ├── index.js           # Public data-layer exports (used by tests)
│   │   ├── client.js          # Live/reference client, revision pinning
│   │   ├── reference.js       # Contract-shaped responses from reference data
│   │   └── errors.js          # APIError
│   ├── hooks/                 # useRequest, useTheme, useReferenceData
│   ├── utils/                 # Formatting (exact decimals), filters, cn()
│   ├── pages/                 # Explorer, Portfolio, RiskIntelligence, Evidence
│   ├── components/
│   │   ├── layout/            # Sidebar, Topbar, SourceBanner, Footer, navigation
│   │   ├── common/            # ErrorBox, Loading, Metric, Pagination, MonthSelect…
│   │   ├── filters/           # Identity filter panel and chips
│   │   ├── inspector/         # Project drawer: overview, history, provenance
│   │   └── Connection.jsx     # Data connection dialog
│   └── styles/global.css
└── tests/
    ├── contract.test.mjs      # Unit tests (npm test)
    ├── live-api.mjs           # Optional check against a running, imported API
    └── risk-browser-smoke.mjs # Headless Chromium smoke test (CI, Linux)
```

## Builds and connections

Production same-origin build: `VITE_API_BASE_URL=/api/v1 npm run build` (PowerShell:
`$env:VITE_API_BASE_URL='/api/v1'; npm run build`). Serve `dist` using
SENTINEL_FRONTEND_DIR on the backend (the Dockerfile does this). A build without
VITE_API_BASE_URL defaults to reference examples, for static hosting.
A separate HTTPS API can still be selected through Data connection; connections
are checked before applying. VITE_ variables become public browser code, so never
put secrets in them.

## Further checks

The optional live check is
`SENTINEL_TEST_API_BASE=http://127.0.0.1:8000/api/v1 node tests/live-api.mjs`.
This check requires the complete validated dataset, not a fixture-only database.

`node tests/risk-browser-smoke.mjs` runs after `npm run build`. It uses
`@sparticuz/chromium`, which provides a Linux binary, so it runs in CI rather than
on Windows/macOS.
