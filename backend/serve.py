"""Start the local API, or the public production service."""
import os
import uvicorn
from .app import create_app
from .access import AccessSettings

if __name__ == "__main__":
    access = AccessSettings.from_env()
    host = os.environ.get("API_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "::1"} and not access.production:
        raise SystemExit("Non-loopback API_HOST requires APP_ENV=production")
    uvicorn.run(create_app(), host=host, port=int(os.environ.get("PORT", os.environ.get("API_PORT", "8000"))))
