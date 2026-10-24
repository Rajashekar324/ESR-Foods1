"""
Database configuration for ESR Foods
"""
from pathlib import Path
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateColumn
import os
import logging
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger(__name__)

# Keep local databases beside the project. Render's filesystem is ephemeral unless
# a persistent disk is mounted, so resolve relative SQLite URLs under that disk.
is_render = os.getenv("RENDER", "").lower() in {"1", "true", "yes"} or bool(os.getenv("RENDER_SERVICE_ID"))
render_data_dir = Path(os.getenv("RENDER_DISK_PATH", "/var/data"))
default_database_url = (
    f"sqlite:///{render_data_dir / 'esr_foods.db'}"
    if is_render
    else "sqlite:///esr_foods.db"
)
DATABASE_URL = os.getenv("DATABASE_URL", default_database_url)
database_url = make_url(DATABASE_URL)
if database_url.get_backend_name() == "sqlite" and database_url.database not in (None, ":memory:"):
    database_path = Path(database_url.database)
    if not database_path.is_absolute():
        database_path = (render_data_dir if is_render else PROJECT_ROOT) / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_url = database_url.set(database=str(database_path.resolve()))
    SQLITE_DATABASE_PATH = str(database_path.resolve())
else:
    SQLITE_DATABASE_PATH = None

# Railway commonly supplies postgresql:// or postgres:// URLs. Select psycopg 3
# explicitly so SQLAlchemy does not try to load the unrelated psycopg2 driver.
if database_url.drivername in {"postgres", "postgresql"}:
    database_url = database_url.set(drivername="postgresql+psycopg")

# Create engine
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.get_backend_name() == "sqlite" else {},
    echo=False,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize legacy SQLite databases or verify a versioned Alembic schema."""
    dialect_name = engine.dialect.name
    default_mode = "alembic" if dialect_name == "postgresql" else "legacy"
    schema_mode = os.getenv("DATABASE_SCHEMA_MODE", default_mode).strip().lower()

    if schema_mode == "legacy":
        _initialize_legacy_schema()
        return
    if schema_mode != "alembic":
        raise RuntimeError("DATABASE_SCHEMA_MODE must be either 'legacy' or 'alembic'.")

    # Alembic is run explicitly during deployment. Startup only verifies that its
    # schema and the last-admin protection are present; it never runs migrations.
    with engine.connect() as conn:
        inspector = inspect(conn)
        if not inspector.has_table("alembic_version"):
            raise RuntimeError("Alembic schema is not installed; run 'alembic upgrade head' before startup.")

        if dialect_name == "sqlite":
            trigger_count = conn.execute(text("""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type = 'trigger'
                  AND name IN ('prevent_last_active_admin_update', 'prevent_last_active_admin_delete')
            """)).scalar_one()
        elif dialect_name == "postgresql":
            trigger_count = conn.execute(text("""
                SELECT COUNT(*)
                FROM pg_trigger AS t
                JOIN pg_class AS tbl ON tbl.oid = t.tgrelid
                WHERE tbl.relname = 'users'
                  AND t.tgname IN (
                      'prevent_last_active_admin_insert',
                      'prevent_last_active_admin_update',
                      'prevent_last_active_admin_delete'
                  )
                  AND NOT t.tgisinternal
            """)).scalar_one()
        else:
            raise RuntimeError(f"Alembic schema verification is unsupported for dialect '{dialect_name}'.")

        expected_trigger_count = 3 if dialect_name == "postgresql" else 2
        if trigger_count != expected_trigger_count:
            raise RuntimeError("Alembic schema is missing last-active-admin protection triggers.")
        if dialect_name == "postgresql":
            counts = conn.execute(text("""
                SELECT g.active_admin_count,
                       (SELECT COUNT(*) FROM users AS u JOIN roles AS r ON r.id = u.role_id
                        WHERE u.is_active AND u.approval_status = 'approved' AND r.name = 'admin')
                FROM esr_admin_guard AS g WHERE g.id = 1
            """)).one_or_none()
            if counts is None or counts[0] != counts[1]:
                raise RuntimeError("PostgreSQL active-admin guard is missing or inconsistent.")

    logger.info("Alembic-managed schema verified (dialect=%s).", dialect_name)


def _initialize_legacy_schema():
    """
    Preserve existing create_all/column-upgrade behavior for legacy deployment.
    """
    from backend.models import (
        user, product, vendor, restaurant, customer,
        purchase, order, invoice, payment, expense,
        batch, stock_movement, notification, audit_log, setting
    )
    try:
        with engine.begin() as conn:
            if conn.dialect.name == "sqlite":
                # SQLite's legacy driver mode does not begin transactions for DDL.
                conn.exec_driver_sql("BEGIN IMMEDIATE")
            Base.metadata.create_all(bind=conn)

            def add_column_if_missing(table_name, column):
                existing = {item["name"] for item in inspect(conn).get_columns(table_name)}
                if column.name not in existing:
                    preparer = conn.dialect.identifier_preparer
                    table = preparer.quote(table_name)
                    column_ddl = str(CreateColumn(column).compile(dialect=conn.dialect))
                    for foreign_key in column.foreign_keys:
                        target_table, target_column = foreign_key.target_fullname.split(".", 1)
                        column_ddl += (
                            f" REFERENCES {preparer.quote(target_table)}"
                            f" ({preparer.quote(target_column)})"
                        )
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_ddl}"))

            add_column_if_missing("payments", Column("purchase_id", Integer))
            add_column_if_missing("payments", Column("expense_id", Integer))
            add_column_if_missing(
                "payments",
                Column("status", String(20), nullable=False, server_default=text("'completed'")),
            )
            add_column_if_missing("payments", Column("category", String(50)))
            add_column_if_missing("payments", Column("paid_to", String(200)))

            user_columns = {item["name"] for item in inspect(conn).get_columns("users")}
            if "approval_status" not in user_columns:
                add_column_if_missing(
                    "users",
                    Column("approval_status", String(20), nullable=False, server_default=text("'approved'")),
                )
                conn.execute(text("UPDATE users SET approval_status = 'disabled' WHERE is_active = 0"))
            add_column_if_missing(
                "users",
                Column("failed_login_attempts", Integer, nullable=False, server_default=text("0")),
            )
            add_column_if_missing("users", Column("locked_until", DateTime(timezone=True)))
            add_column_if_missing(
                "users",
                Column("token_version", Integer, nullable=False, server_default=text("0")),
            )
            add_column_if_missing(
                "payments",
                Column("customer_id", Integer, ForeignKey("retail_customers.id")),
            )
            add_column_if_missing(
                "vendors",
                Column("credit_adjustments", Float, nullable=False, server_default=text("0")),
            )

            if conn.dialect.name == "sqlite":
                conn.execute(text("""
                    CREATE TRIGGER IF NOT EXISTS prevent_last_active_admin_update
                    BEFORE UPDATE OF is_active, approval_status, role_id ON users
                    WHEN OLD.is_active = 1
                     AND OLD.approval_status = 'approved'
                     AND EXISTS (SELECT 1 FROM roles WHERE id = OLD.role_id AND name = 'admin')
                     AND NOT (NEW.is_active = 1 AND NEW.approval_status = 'approved'
                              AND EXISTS (SELECT 1 FROM roles WHERE id = NEW.role_id AND name = 'admin'))
                     AND (SELECT COUNT(*) FROM users u JOIN roles r ON r.id = u.role_id
                          WHERE u.is_active = 1 AND u.approval_status = 'approved' AND r.name = 'admin') <= 1
                    BEGIN
                        SELECT RAISE(ABORT, 'The application must retain at least one active Admin.');
                    END;
                """))
                conn.execute(text("""
                    CREATE TRIGGER IF NOT EXISTS prevent_last_active_admin_delete
                    BEFORE DELETE ON users
                    WHEN OLD.is_active = 1
                     AND OLD.approval_status = 'approved'
                     AND EXISTS (SELECT 1 FROM roles WHERE id = OLD.role_id AND name = 'admin')
                     AND (SELECT COUNT(*) FROM users u JOIN roles r ON r.id = u.role_id
                          WHERE u.is_active = 1 AND u.approval_status = 'approved' AND r.name = 'admin') <= 1
                    BEGIN
                        SELECT RAISE(ABORT, 'The application must retain at least one active Admin.');
                    END;
                """))
            elif conn.dialect.name == "postgresql":
                actual_admin_count = conn.execute(text("""
                    SELECT COUNT(*) FROM users AS u JOIN roles AS r ON r.id = u.role_id
                    WHERE u.is_active AND u.approval_status = 'approved' AND r.name = 'admin'
                """)).scalar_one()
                if actual_admin_count < 1:
                    raise RuntimeError("Cannot initialize PostgreSQL protection without an active approved Admin.")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS esr_admin_guard (
                        id SMALLINT PRIMARY KEY CHECK (id = 1),
                        active_admin_count INTEGER NOT NULL CHECK (active_admin_count >= 0)
                    )
                """))
                conn.execute(text("""
                    INSERT INTO esr_admin_guard (id, active_admin_count)
                    VALUES (1, :count)
                    ON CONFLICT (id) DO NOTHING
                """), {"count": actual_admin_count})
                guarded_count = conn.execute(text(
                    "SELECT active_admin_count FROM esr_admin_guard WHERE id = 1"
                )).scalar_one()
                if guarded_count != actual_admin_count:
                    raise RuntimeError("PostgreSQL active-admin guard count is inconsistent with users.")
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION esr_prevent_last_active_admin_change()
                    RETURNS trigger
                    LANGUAGE plpgsql
                    AS $$
                    DECLARE
                        old_is_admin BOOLEAN;
                        new_is_admin BOOLEAN := FALSE;
                    BEGIN
                        IF TG_OP <> 'INSERT' THEN
                            SELECT EXISTS (
                                SELECT 1 FROM roles WHERE id = OLD.role_id AND name = 'admin'
                            ) AND OLD.is_active AND OLD.approval_status = 'approved' INTO old_is_admin;
                        END IF;
                        IF TG_OP <> 'DELETE' THEN
                            SELECT EXISTS (
                                SELECT 1 FROM roles WHERE id = NEW.role_id AND name = 'admin'
                            ) AND NEW.is_active AND NEW.approval_status = 'approved' INTO new_is_admin;
                        END IF;

                        IF TG_OP = 'INSERT' AND new_is_admin THEN
                            UPDATE esr_admin_guard SET active_admin_count = active_admin_count + 1 WHERE id = 1;
                            RETURN NEW;
                        ELSIF TG_OP = 'DELETE' AND old_is_admin THEN
                            UPDATE esr_admin_guard
                            SET active_admin_count = active_admin_count - 1
                            WHERE id = 1 AND active_admin_count > 1;
                            IF NOT FOUND THEN
                                RAISE EXCEPTION 'The application must retain at least one active Admin.'
                                    USING ERRCODE = '23514';
                            END IF;
                            RETURN OLD;
                        ELSIF TG_OP = 'UPDATE' AND old_is_admin AND NOT new_is_admin THEN
                            UPDATE esr_admin_guard
                            SET active_admin_count = active_admin_count - 1
                            WHERE id = 1 AND active_admin_count > 1;
                            IF NOT FOUND THEN
                                RAISE EXCEPTION 'The application must retain at least one active Admin.'
                                    USING ERRCODE = '23514';
                            END IF;
                        ELSIF TG_OP = 'UPDATE' AND NOT old_is_admin AND new_is_admin THEN
                            UPDATE esr_admin_guard SET active_admin_count = active_admin_count + 1 WHERE id = 1;
                        END IF;
                        RETURN NEW;
                    END;
                    $$;
                """))
                conn.execute(text("DROP TRIGGER IF EXISTS prevent_last_active_admin_insert ON users"))
                conn.execute(text("DROP TRIGGER IF EXISTS prevent_last_active_admin_update ON users"))
                conn.execute(text("DROP TRIGGER IF EXISTS prevent_last_active_admin_delete ON users"))
                conn.execute(text("""
                    CREATE TRIGGER prevent_last_active_admin_insert
                    BEFORE INSERT ON users
                    FOR EACH ROW EXECUTE FUNCTION esr_prevent_last_active_admin_change()
                """))
                conn.execute(text("""
                    CREATE TRIGGER prevent_last_active_admin_update
                    BEFORE UPDATE OF is_active, approval_status, role_id ON users
                    FOR EACH ROW EXECUTE FUNCTION esr_prevent_last_active_admin_change()
                """))
                conn.execute(text("""
                    CREATE TRIGGER prevent_last_active_admin_delete
                    BEFORE DELETE ON users
                    FOR EACH ROW EXECUTE FUNCTION esr_prevent_last_active_admin_change()
                """))
    except Exception as exc:
        logger.error(
            "Database initialization/migration failed (dialect=%s, error_type=%s).",
            database_url.get_backend_name(),
            type(exc).__name__,
        )
        raise RuntimeError("Database schema initialization failed; startup cannot safely continue.") from None

    logger.info(
        "Database schema initialized (dialect=%s, sqlite_path=%s).",
        database_url.get_backend_name(),
        SQLITE_DATABASE_PATH or "not applicable",
    )

