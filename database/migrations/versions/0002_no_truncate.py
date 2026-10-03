"""Guard immutable datasets against statement-level truncation."""
from alembic import op

revision = "0002_no_truncate"
down_revision = "0001_monitoring"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("dataset_revisions", "monthly_snapshots", "adjacent_comparisons"):
        op.execute(f"CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON {table} "
                   "FOR EACH STATEMENT EXECUTE FUNCTION sentinel_immutable()")


def downgrade():
    for table in ("dataset_revisions", "monthly_snapshots", "adjacent_comparisons"):
        op.execute(f"DROP TRIGGER immutable_truncate ON {table}")
