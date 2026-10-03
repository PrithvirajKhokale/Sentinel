# Sentinel — Database Design

## Database

PostgreSQL

## ORM

SQLAlchemy

## Purpose

The database stores structured project and application information required by the Sentinel platform.

## Main Data Concepts

- Projects
- Project monitoring snapshots
- Project progress information
- Risk predictions
- Risk assessments
- Relevant project events/issues

## Relationships

[Add ER diagram after schema is finalized.]

## Design Principle

The database schema should remain separate from the ML processing pipeline so that data storage and predictive processing remain modular.
## Local monitoring database implementation

Alembic migrations now define immutable dataset_revisions, monthly_snapshots and adjacent_comparisons plus a singleton active_dataset pointer. Snapshot primary key is (version, project_code, report_month); comparisons reference both observed snapshots. JSON payloads retain raw values, normalized decimal strings, nulls and source provenance. PostgreSQL triggers prohibit revision-row UPDATE, DELETE and TRUNCATE; import/activation uses one transaction and locks the active pointer. No prediction tables are implemented. See [local setup and rollback checks](backend-local.md).
