# Database migrations

Alembic is configured to load the SQLAlchemy `Base.metadata` and `DATABASE_URL` from `backend.database`. The initial revision `6cfb368f23a5` creates the current application schema and dialect-specific last-active-admin protection. It contains schema only, no production data. Review and test it against a disposable/staging database before any production change. Do not point autogeneration at the live production database as a substitute for review.

Typical staging workflow:

1. Set `DATABASE_URL` to the intended staging database URL. Do not set `POSTGRES_DATABASE_URL` in place of it unless deliberately testing that database.
2. Inspect and confirm that the PostgreSQL staging database is empty or contains only explicitly disposable prior test/schema state. Stop if unexpected data is found; do not drop or overwrite it.
3. Review and test the checked-in revision, including enum types, foreign keys, `esr_admin_guard` initialized to zero for a clean first install, the PostgreSQL guard function, and all three admin triggers.
4. Explicitly apply the reviewed revision with `alembic upgrade head`, then verify with `alembic current` and inspect the schema.
5. For app startup against an Alembic-managed schema, set `DATABASE_SCHEMA_MODE=alembic`. Startup verifies `alembic_version`, the guard row, and all three PostgreSQL admin-protection triggers; it does not execute Alembic migrations.

SQLite keeps the legacy startup mode (`create_all` plus additive compatibility columns and its existing triggers) unless `DATABASE_SCHEMA_MODE=alembic` is explicitly set. This behavior is intentional for the current Railway SQLite production service. No Railway database has been migrated by this repository preparation.
