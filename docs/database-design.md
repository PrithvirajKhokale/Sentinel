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