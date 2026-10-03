from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Revision(Base):
    __tablename__ = "dataset_revisions"
    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    manifest: Mapped[str] = mapped_column(Text)
    reports: Mapped[list] = mapped_column(JSON)
    warnings: Mapped[list] = mapped_column(JSON)


class ActiveDataset(Base):
    __tablename__ = "active_dataset"
    __table_args__ = (CheckConstraint("id = 1"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str | None] = mapped_column(ForeignKey("dataset_revisions.version"), nullable=True)


class Snapshot(Base):
    __tablename__ = "monthly_snapshots"
    version: Mapped[str] = mapped_column(ForeignKey("dataset_revisions.version"), primary_key=True)
    project_code: Mapped[str] = mapped_column(String, primary_key=True)
    report_month: Mapped[str] = mapped_column(String(7), primary_key=True)
    project_name: Mapped[str] = mapped_column(Text)
    ministry: Mapped[str] = mapped_column(Text, index=True)
    sector: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    agency: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)


class Comparison(Base):
    __tablename__ = "adjacent_comparisons"
    __table_args__ = (
        ForeignKeyConstraint(["version", "project_code", "before_month"],
                             ["monthly_snapshots.version", "monthly_snapshots.project_code", "monthly_snapshots.report_month"]),
        ForeignKeyConstraint(["version", "project_code", "after_month"],
                             ["monthly_snapshots.version", "monthly_snapshots.project_code", "monthly_snapshots.report_month"]),
    )
    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_code: Mapped[str] = mapped_column(String, primary_key=True)
    before_month: Mapped[str] = mapped_column(String(7), primary_key=True)
    after_month: Mapped[str] = mapped_column(String(7), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
