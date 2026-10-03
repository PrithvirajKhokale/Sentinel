from alembic import context
from backend.db import engine_from_env
from backend.models import Base


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


provided = context.config.attributes.get("connection")
if provided is not None:
    migrate(provided)
else:
    with engine_from_env().connect() as connection:
        migrate(connection)
