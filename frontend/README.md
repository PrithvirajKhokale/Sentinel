# Sentinel React frontend

The original private Sites design, including dark mode, is now versioned in the
Sentinel repository. React + Vite consumes the unchanged four-endpoint API contract.

Run the backend on 127.0.0.1:8000, then `npm ci` and `npm run dev` in this folder.
Development defaults to the real API via Vite's `/api` proxy. An unavailable API
stays an error; switch explicitly to Reference examples to use the checked samples.

Production same-origin build: `VITE_API_BASE_URL=/api/v1 npm run build` (PowerShell:
`$env:VITE_API_BASE_URL='/api/v1'; npm run build`). Serve `dist` using
SENTINEL_FRONTEND_DIR on the backend. A build without VITE_API_BASE_URL defaults to
reference examples, suitable for the existing private static Sites deployment.
A separate HTTPS API can still be selected through Data connection. Connections
are checked before applying; bearer tokens are held only in memory. Never put a
token in a VITE_ environment variable: those variables become public browser code.

`npm test` checks the contract/client invariants. The optional live check is
`SENTINEL_TEST_API_BASE=http://127.0.0.1:8000/api/v1 node tests/live-api.mjs`.
Pass SENTINEL_TEST_API_TOKEN through the environment when API auth is enabled.
This check requires the complete validated dataset, not a fixture-only database.
