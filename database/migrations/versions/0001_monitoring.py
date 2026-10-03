"""Immutable revisions, snapshots, comparisons and transactional active pointer."""
from alembic import op
import sqlalchemy as sa

revision = "0001_monitoring"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("dataset_revisions",
        sa.Column("version",sa.String(64),primary_key=True),
        sa.Column("manifest",sa.Text(),nullable=False),
        sa.Column("reports",sa.JSON(),nullable=False),
        sa.Column("warnings",sa.JSON(),nullable=False))
    op.create_table("active_dataset",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("version",sa.String(64),sa.ForeignKey("dataset_revisions.version")),
        sa.CheckConstraint("id = 1"))
    op.create_table("monthly_snapshots",
        sa.Column("version",sa.String(64),sa.ForeignKey("dataset_revisions.version"),primary_key=True),
        sa.Column("project_code",sa.String(),primary_key=True),
        sa.Column("report_month",sa.String(7),primary_key=True),
        *[sa.Column(f,sa.Text(),nullable=False) for f in ("project_name","ministry","sector","state","agency")],
        sa.Column("payload",sa.JSON(),nullable=False))
    op.create_index("ix_monthly_snapshots_ministry","monthly_snapshots",["ministry"])
    op.create_table("adjacent_comparisons",
        sa.Column("version",sa.String(64),primary_key=True),
        sa.Column("project_code",sa.String(),primary_key=True),
        sa.Column("before_month",sa.String(7),primary_key=True),
        sa.Column("after_month",sa.String(7),primary_key=True),
        sa.Column("payload",sa.JSON(),nullable=False),
        sa.ForeignKeyConstraint(["version","project_code","before_month"],["monthly_snapshots.version","monthly_snapshots.project_code","monthly_snapshots.report_month"]),
        sa.ForeignKeyConstraint(["version","project_code","after_month"],["monthly_snapshots.version","monthly_snapshots.project_code","monthly_snapshots.report_month"]))
    op.execute("INSERT INTO active_dataset (id, version) VALUES (1, NULL)")
    op.execute("""CREATE FUNCTION sentinel_immutable() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'Dataset revision rows are immutable'; END;
    $$ LANGUAGE plpgsql""")
    for table in ("dataset_revisions", "monthly_snapshots", "adjacent_comparisons"):
        op.execute(f"CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON {table} "
                   "FOR EACH ROW EXECUTE FUNCTION sentinel_immutable()")


def downgrade():
    for table in ("adjacent_comparisons", "monthly_snapshots", "dataset_revisions"):
        op.execute(f"DROP TRIGGER immutable_rows ON {table}")
    op.execute("DROP FUNCTION sentinel_immutable()")
    for table in ("adjacent_comparisons","monthly_snapshots","active_dataset","dataset_revisions"):
        op.drop_table(table)
