import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from .access import AccessSettings


def engine_from_env():
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL must identify a local PostgreSQL database")
    url = make_url(value)
    access = AccessSettings.from_env()
    if access.production and url.drivername in {"postgres", "postgresql"}:
        # Render's generated URL uses the generic PostgreSQL scheme.
        url = url.set(drivername="postgresql+psycopg")
    if access.production and not url.query.get("sslmode") and os.environ.get("SENTINEL_DB_SSLMODE"):
        url = url.update_query_dict({"sslmode": os.environ["SENTINEL_DB_SSLMODE"]})
    if url.drivername != "postgresql+psycopg":
        raise ValueError("PostgreSQL with psycopg is required")
    if not access.production and url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Only loopback PostgreSQL is supported in development")
    if access.production and (not url.host or url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}):
        raise ValueError("Production PostgreSQL requires a host and explicit TLS sslmode")
    return create_engine(url, pool_pre_ping=True)
