"""Deployment environment settings. The read-only API is public; there is no authentication."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AccessSettings:
    production: bool

    @classmethod
    def from_env(cls):
        environment = os.environ.get("APP_ENV", "development")
        if environment not in {"development", "production"}:
            raise ValueError("APP_ENV must be development or production")
        return cls(environment == "production")
