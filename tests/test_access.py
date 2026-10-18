"""Access checks run without a database or source PDFs."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.access import AccessSettings
from backend.db import engine_from_env

TOKEN = "test-only-" + "x" * 40
ORIGIN = "https://sentinel-project-explorer.expertsky64.chatgpt.site"


class AccessTests(unittest.TestCase):
    def client(self, **env):
        context = patch.dict(os.environ, {"APP_ENV": "development", "SENTINEL_API_TOKEN": "",
            "SENTINEL_ALLOWED_ORIGINS": "", "SENTINEL_FRONTEND_DIR": "", "SENTINEL_PUBLIC_ACCESS": "false", **env})
        context.start(); self.addCleanup(context.stop)
        client = TestClient(create_app(engine=object()), raise_server_exceptions=False)
        self.addCleanup(client.close)
        return client

    def test_missing_and_invalid_token_never_reach_database(self):
        client = self.client(APP_ENV="production", SENTINEL_API_TOKEN=TOKEN)
        for path in ["/api/v1/projects?report_month=2026-08", "/api/v1/projects/701530?report_month=2026-07",
                     "/api/v1/projects/611752/history", "/api/v1/portfolio-summary?report_month=2026-08"]:
            for headers in [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic " + TOKEN}]:
                response = client.get(path, headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")
                self.assertNotIn(TOKEN, response.text)
                self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_valid_token_reaches_query_validation_and_health_is_minimal(self):
        client = self.client(APP_ENV="production", SENTINEL_API_TOKEN=TOKEN)
        response = client.get("/api/v1/projects", headers={"Authorization": "Bearer " + TOKEN})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(client.get("/healthz").json(), {"status": "ok"})
        for path in ["/docs", "/openapi.json"]:
            self.assertEqual(client.get(path, headers={"Authorization": "Bearer " + TOKEN}).status_code, 404)

    def test_cors_preflight_exact_origin_and_authentication_errors(self):
        client = self.client(APP_ENV="production", SENTINEL_API_TOKEN=TOKEN, SENTINEL_ALLOWED_ORIGINS=ORIGIN)
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "Authorization"}
        response=client.options("/api/v1/projects", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], ORIGIN)
        response=client.get("/api/v1/projects", headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["access-control-allow-origin"], ORIGIN)
        for origin in ["https://untrusted.example", ORIGIN + ".evil.example"]:
            response=client.options("/api/v1/projects", headers={**headers, "Origin": origin})
            self.assertNotIn("access-control-allow-origin", response.headers)

    def test_production_configuration_fails_closed(self):
        for settings in [{"SENTINEL_API_TOKEN": ""}, {"SENTINEL_API_TOKEN": "short"},
                         {"SENTINEL_ALLOWED_ORIGINS": "*"}, {"SENTINEL_ALLOWED_ORIGINS": "http://example.com"},
                         {"SENTINEL_ALLOWED_ORIGINS": ORIGIN + "/path"}]:
            with patch.dict(os.environ, {"APP_ENV": "production", "SENTINEL_API_TOKEN": TOKEN,
                                        "SENTINEL_ALLOWED_ORIGINS": "", **settings}):
                with self.assertRaises(ValueError): AccessSettings.from_env()
        with patch.dict(os.environ, APP_ENV="production", SENTINEL_API_TOKEN=TOKEN,
                        DATABASE_URL="postgresql+psycopg://u:p@db.example/sentinel", SENTINEL_ALLOWED_ORIGINS=""):
            with self.assertRaisesRegex(ValueError, "TLS"): engine_from_env()

    def test_frontend_served_on_same_origin_without_bypassing_api_auth(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "index.html").write_text("<h1>Sentinel</h1>")
            client = self.client(SENTINEL_API_TOKEN=TOKEN, SENTINEL_FRONTEND_DIR=directory)
            self.assertEqual(client.get("/").status_code, 200)
            self.assertIn("Sentinel", client.get("/").text)
            self.assertEqual(client.get("/api/v1/projects?report_month=2026-08").status_code, 401)
            self.assertEqual(client.get("/api/no-such-route").status_code, 401)
            self.assertEqual(client.get("/api/no-such-route", headers={"Authorization":"Bearer "+TOKEN}).status_code,404)

    def test_public_mode_serves_without_token_and_allows_any_origin(self):
        client = self.client(APP_ENV="production", SENTINEL_PUBLIC_ACCESS="true")
        response = client.get("/api/v1/projects", headers={"Origin": "https://anyone.example"})
        # No 401: requests reach contract validation, and CORS is open without credentials.
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")
        self.assertNotIn("access-control-allow-credentials", response.headers)
        preflight = client.options("/api/v1/projects", headers={"Origin": "https://anyone.example",
                                   "Access-Control-Request-Method": "GET"})
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(client.options("/api/v1/projects", headers={"Origin": "https://anyone.example",
                         "Access-Control-Request-Method": "POST"}).status_code, 400)
        self.assertEqual(client.get("/openapi.json").status_code, 200)

    def test_public_mode_rejects_ambiguous_configuration(self):
        for settings in [{"SENTINEL_API_TOKEN": TOKEN}, {"SENTINEL_ALLOWED_ORIGINS": ORIGIN},
                         {"SENTINEL_PUBLIC_ACCESS": "yes"}]:
            with patch.dict(os.environ, {"APP_ENV": "production", "SENTINEL_API_TOKEN": "",
                                        "SENTINEL_ALLOWED_ORIGINS": "", "SENTINEL_PUBLIC_ACCESS": "true", **settings}):
                with self.assertRaises(ValueError): AccessSettings.from_env()

    def test_local_unauthenticated_mode_retains_contract_validation(self):
        client=self.client()
        self.assertEqual(client.get("/api/v1/projects").status_code, 422)

    def test_render_database_url_uses_psycopg_and_explicit_tls(self):
        with patch.dict(os.environ, APP_ENV="production", SENTINEL_API_TOKEN=TOKEN,
                        DATABASE_URL="postgresql://user:placeholder@db.example/sentinel",
                        SENTINEL_ALLOWED_ORIGINS="", SENTINEL_DB_SSLMODE="require"):
            with patch("backend.db.create_engine") as create:
                engine_from_env()
                url = create.call_args.args[0]
                self.assertEqual(url.drivername, "postgresql+psycopg")
                self.assertEqual(url.query["sslmode"], "require")
