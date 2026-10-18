"""Start the local API, or an explicitly configured (authenticated or public) production service."""
import os
import uvicorn
from .app import create_app
from .access import AccessSettings

if __name__ == "__main__":
    access = AccessSettings.from_env()
    host = os.environ.get("API_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "::1"} and not access.production:
        raise SystemExit("Non-loopback API_HOST requires APP_ENV=production with a token or SENTINEL_PUBLIC_ACCESS=true")
    uvicorn.run(create_app(), host=host, port=int(os.environ.get("PORT", os.environ.get("API_PORT", "8000"))))
