"""Explicit bearer authentication and exact browser-origin configuration."""
from dataclasses import dataclass
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class AccessSettings:
    production: bool
    token: str
    origins: tuple[str, ...]

    @classmethod
    def from_env(cls):
        environment = os.environ.get("APP_ENV", "development")
        if environment not in {"development", "production"}:
            raise ValueError("APP_ENV must be development or production")
        token = os.environ.get("SENTINEL_API_TOKEN", "")
        production = environment == "production"
        if (production or token) and (len(token) < 32 or not token.isascii() or any(c.isspace() for c in token)):
            raise ValueError("SENTINEL_API_TOKEN must contain at least 32 non-whitespace ASCII characters")
        origins = tuple(dict.fromkeys(x.strip() for x in os.environ.get("SENTINEL_ALLOWED_ORIGINS", "").split(",") if x.strip()))
        for origin in origins:
            u = urlsplit(origin)
            if (u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password
                    or u.path or u.query or u.fragment or "*" in origin
                    or (production and u.scheme != "https")):
                raise ValueError("Allowed origins must be exact origins, using HTTPS in production")
        return cls(production, token, origins)
