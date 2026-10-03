"""Run the unauthenticated local demo on loopback only."""
import os
import uvicorn
from .app import create_app

if __name__ == "__main__":
    host = os.environ.get("API_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "::1"}:
        raise SystemExit("Only loopback API_HOST is allowed; authentication is required before shared deployment")
    uvicorn.run(create_app(),host=host,port=int(os.environ.get("API_PORT","8000")))
