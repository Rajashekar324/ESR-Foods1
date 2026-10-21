"""
Database configuration for ESR Foods
"""
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
DATABASE_URL = database_url.render_as_string(hide_password=False)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if database_url.get_backend_name() == "sqlite" else {},
    echo=False
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
    """
    Initialize database - create all tables and perform simple column migrations
    """
    from backend.models import (
        user, product, vendor, restaurant, customer,
        purchase, order, invoice, payment, expense,
        batch, stock_movement, notification, audit_log, setting
    )
    try:
        Base.metadata.create_all(bind=engine)

        # Auto migrate sqlite columns if missing
        with engine.connect() as conn:
            # Check payments table columns
            existing_cols = {column["name"] for column in inspect(engine).get_columns("payments")}
            
            from sqlalchemy import text
            if "purchase_id" not in existing_cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN purchase_id INTEGER"))
            if "expense_id" not in existing_cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN expense_id INTEGER"))
            if "status" not in existing_cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN status VARCHAR(20) DEFAULT 'completed'"))
            if "category" not in existing_cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN category VARCHAR(50)"))
            if "paid_to" not in existing_cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN paid_to VARCHAR(200)"))
            user_cols = {column["name"] for column in inspect(engine).get_columns("users")}
            if "approval_status" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN approval_status VARCHAR(20) NOT NULL DEFAULT 'approved'"))
                conn.execute(text("UPDATE users SET approval_status = 'disabled' WHERE is_active = 0"))
            if "failed_login_attempts" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0"))
            if "locked_until" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN locked_until DATETIME"))
            if "token_version" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"))
            payment_cols = {column["name"] for column in inspect(engine).get_columns("payments")}
            if "customer_id" not in payment_cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN customer_id INTEGER REFERENCES retail_customers(id)"))
            vendor_cols = {column["name"] for column in inspect(engine).get_columns("vendors")}
            if "credit_adjustments" not in vendor_cols:
                conn.execute(text("ALTER TABLE vendors ADD COLUMN credit_adjustments FLOAT DEFAULT 0"))
            if database_url.get_backend_name() == "sqlite":
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
            conn.commit()
    except Exception as exc:
        logger.exception("Database initialization/migration failed (sqlite_path=%s).", SQLITE_DATABASE_PATH)
        raise RuntimeError("Database schema migration failed; startup cannot safely continue.") from exc

    logger.info(
        "Database schema initialized (dialect=%s, sqlite_path=%s).",
        database_url.get_backend_name(),
        SQLITE_DATABASE_PATH or "not applicable",
    )

