"""Explicit bearer authentication, public read-only mode and browser-origin configuration."""
from dataclasses import dataclass
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class AccessSettings:
    production: bool
    token: str
    origins: tuple[str, ...]
    # Public mode: read-only API without a token, CORS open to any origin.
    public: bool = False

    @classmethod
    def from_env(cls):
        environment = os.environ.get("APP_ENV", "development")
        if environment not in {"development", "production"}:
            raise ValueError("APP_ENV must be development or production")
        token = os.environ.get("SENTINEL_API_TOKEN", "")
        production = environment == "production"
        public = os.environ.get("SENTINEL_PUBLIC_ACCESS", "false").lower()
        if public not in {"true", "false"}:
            raise ValueError("SENTINEL_PUBLIC_ACCESS must be true or false")
        public = public == "true"
        if public:
            # Refuse an ambiguous mix: a configured token would silently stop protecting anything.
            if token or os.environ.get("SENTINEL_ALLOWED_ORIGINS", "").strip():
                raise ValueError("Public access cannot be combined with SENTINEL_API_TOKEN or SENTINEL_ALLOWED_ORIGINS")
            return cls(production, "", (), public=True)
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
