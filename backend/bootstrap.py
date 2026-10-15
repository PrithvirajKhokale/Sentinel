"""Initialize a baked, validated revision before starting the hosted API."""
import hashlib
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session
from .db import engine_from_env
from .import_dataset import ROOT, validate_bundle, archive_bundle, activate_bundle
from .models import ActiveDataset, Revision


def initialize(engine):
    # Keep schema changes within Alembic and serialize first-start initialization.
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT pg_advisory_lock(7569321)")
        connection.commit()
        try:
            cfg = Config(str(ROOT / "alembic.ini"))
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
            connection.commit()
            manifest = (ROOT / "docs/examples/dataset-manifest.json").read_text(encoding="utf-8")
            expected = hashlib.sha256(manifest.encode()).hexdigest()
            with Session(connection) as session:
                active = session.get(ActiveDataset, 1)
                stored = session.get(Revision, expected)
                ready = active is not None and active.version == expected and stored is not None and stored.manifest == manifest
            connection.rollback()
            if ready:
                print("Validated dataset is already active.", flush=True)
                return
            bundle = validate_bundle(ROOT, "docs/examples/dataset-manifest.json")
            archive_bundle(bundle, ROOT / "data/revisions")
            # Use the lock-holding connection so no second database connection is needed.
            activate_bundle(connection, bundle)
            connection.commit()
            print(f"Activated validated dataset: {len(bundle['snapshots'])} snapshots, {len(bundle['comparisons'])} comparisons.", flush=True)
        finally:
            connection.rollback()
            connection.exec_driver_sql("SELECT pg_advisory_unlock(7569321)")
            connection.commit()


if __name__ == "__main__":
    initialize(engine_from_env())
    import runpy
    runpy.run_module("backend.serve", run_name="__main__")
