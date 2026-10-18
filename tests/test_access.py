"""Public access checks run without a database or source PDFs."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.access import AccessSettings
from backend.db import engine_from_env

ORIGIN = "https://anyone.example"
QUERIES = ["/api/v1/projects?report_month=2026-08", "/api/v1/projects/701530?report_month=2026-07",
           "/api/v1/projects/611752/history", "/api/v1/portfolio-summary?report_month=2026-08"]


class AccessTests(unittest.TestCase):
    def client(self, **env):
        context = patch.dict(os.environ, {"APP_ENV": "development", "SENTINEL_FRONTEND_DIR": "", **env})
        context.start(); self.addCleanup(context.stop)
        client = TestClient(create_app(engine=object()), raise_server_exceptions=False)
        self.addCleanup(client.close)
        return client

    def test_production_api_is_public_without_authentication(self):
        client = self.client(APP_ENV="production")
        response = client.get("/api/v1/projects")
        # Requests reach contract validation; no authentication layer exists.
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertNotIn("www-authenticate", response.headers)
        self.assertEqual(client.get("/healthz").json(), {"status": "ok"})
        for path in ["/docs", "/openapi.json"]:
            self.assertEqual(client.get(path).status_code, 200)

    def test_cors_allows_any_origin_for_read_only_requests(self):
        client = self.client(APP_ENV="production")
        response = client.get("/api/v1/projects", headers={"Origin": ORIGIN})
        self.assertEqual(response.headers["access-control-allow-origin"], "*")
        self.assertNotIn("access-control-allow-credentials", response.headers)
        preflight = {"Origin": ORIGIN, "Access-Control-Request-Method": "GET"}
        self.assertEqual(client.options("/api/v1/projects", headers=preflight).status_code, 200)
        self.assertEqual(client.options("/api/v1/projects",
                         headers={**preflight, "Access-Control-Request-Method": "POST"}).status_code, 400)
        for path in QUERIES:
            self.assertEqual(client.post(path).status_code, 405)

    def test_production_database_requires_tls(self):
        with patch.dict(os.environ, APP_ENV="production", DATABASE_URL="postgresql+psycopg://u:p@db.example/sentinel"):
            with self.assertRaisesRegex(ValueError, "TLS"): engine_from_env()
        with patch.dict(os.environ, APP_ENV="staging"):
            with self.assertRaises(ValueError): AccessSettings.from_env()

    def test_frontend_served_on_same_origin_with_api_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "index.html").write_text("<h1>Sentinel</h1>")
            client = self.client(SENTINEL_FRONTEND_DIR=directory)
            self.assertEqual(client.get("/").status_code, 200)
            self.assertIn("Sentinel", client.get("/").text)
            response = client.get("/api/v1/projects")
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_local_mode_retains_contract_validation(self):
        client = self.client()
        self.assertEqual(client.get("/api/v1/projects").status_code, 422)

    def test_render_database_url_uses_psycopg_and_explicit_tls(self):
        with patch.dict(os.environ, APP_ENV="production",
                        DATABASE_URL="postgresql://user:placeholder@db.example/sentinel",
                        SENTINEL_DB_SSLMODE="require"):
            with patch("backend.db.create_engine") as create:
                engine_from_env()
                url = create.call_args.args[0]
                self.assertEqual(url.drivername, "postgresql+psycopg")
                self.assertEqual(url.query["sslmode"], "require")
