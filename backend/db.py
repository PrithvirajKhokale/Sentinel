import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


def engine_from_env():
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL must identify a local PostgreSQL database")
    url = make_url(value)
    if url.drivername != "postgresql+psycopg" or url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Only loopback PostgreSQL with psycopg is supported")
    return create_engine(url, pool_pre_ping=True)
