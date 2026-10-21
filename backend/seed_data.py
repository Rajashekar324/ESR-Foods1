"""
Seed data script for ESR Foods
Run this to initialize the database with default roles and admin user
"""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from backend.database import SessionLocal, init_db
from backend.models.user import User, Role
from backend.models.setting import Setting
from backend.models.product import Category
from backend.auth.security import hash_password, verify_password

logger = logging.getLogger(__name__)


def validate_password(password: str) -> None:
    if (
        len(password) < 12
        or len(password.encode("utf-8")) > 72
        or not any(char.islower() for char in password)
        or not any(char.isupper() for char in password)
        or not any(char.isdigit() for char in password)
    ):
        raise RuntimeError("Password must be 12–72 bytes and contain uppercase, lowercase, and numeric characters.")


def seed_categories(db: Session):
    """Create default categories"""
    categories = [
        Category(name="Fish (Fresh & Frozen)", description="Fresh and frozen fish varieties"),
        Category(name="Prawns & Shrimp", description="Prawns, shrimps, and related shellfish"),
        Category(name="Crab & Shellfish", description="Crabs, oysters, clams, and mussels"),
        Category(name="Squid & Cuttlefish", description="Squid, cuttlefish, and octopus"),
        Category(name="Lobster", description="Fresh and frozen lobsters"),
        Category(name="Frozen Seafood", description="Pre-packaged frozen seafood products"),
        Category(name="Dried Seafood", description="Salted and dried seafood products"),
        Category(name="Value Added & Processed", description="Marinated, battered, or processed seafood items"),
        Category(name="Other Seafood", description="Miscellaneous seafood items")
    ]
    
    for cat in categories:
        if not db.query(Category).filter(Category.name == cat.name).first():
            db.add(cat)
            
    db.commit()
    logger.info("Default product categories verified/seeded.")


def seed_roles(db: Session):
    """Create default roles"""
    roles = [
        Role(name="admin", description="Full system access including user approvals and security settings", permissions="all"),
        Role(name="manager", description="Business operations and financial reporting; no user/security administration", permissions="products,inventory,vendors,purchases,restaurants,customers,orders,invoices,payments,expenses,reports,dashboard"),
        Role(name="staff", description="Restricted internal notifications only; no customer, inventory-value, order, financial, or system-security data", permissions="notifications")
    ]
    
    for role in roles:
        existing_role = db.query(Role).filter(Role.name == role.name).first()
        if not existing_role:
            db.add(role)
        else:
            existing_role.description = role.description
            existing_role.permissions = role.permissions
    
    db.commit()
    logger.info("Default roles verified/seeded.")


def seed_users(db: Session):
    """Create or reconcile the single configured bootstrap Admin account."""
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        raise RuntimeError("Admin role is missing; seed roles before creating the bootstrap Admin.")

    username = os.getenv("ADMIN_USERNAME") or os.getenv("ESR_ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL") or os.getenv("ESR_ADMIN_EMAIL", "admin@esrfoods.com")
    password = os.getenv("ADMIN_PASSWORD") or os.getenv("ESR_ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("Set ADMIN_EMAIL and ADMIN_PASSWORD in the deployment environment to bootstrap the Admin account.")
    validate_password(password)

    by_username = db.query(User).filter(User.username == username).first()
    by_email = db.query(User).filter(User.email == email).first()
    if by_username and by_email and by_username.id != by_email.id:
        raise RuntimeError("ADMIN_USERNAME and ADMIN_EMAIL belong to different existing accounts.")

    admin_user = by_username or by_email
    if admin_user and admin_user.role_id != admin_role.id:
        raise RuntimeError("Configured Admin username/email belongs to a non-admin account.")

    # Reuse an existing administrator if the configured identifiers changed;
    # never create a second bootstrap Admin on redeploy.
    if not admin_user:
        admin_user = db.query(User).filter(User.role_id == admin_role.id).order_by(User.id).first()

    if admin_user:
        conflicting_email = db.query(User).filter(User.email == email, User.id != admin_user.id).first()
        if conflicting_email:
            raise RuntimeError("ADMIN_EMAIL is already assigned to a different account.")
        admin_user.email = email
        admin_user.is_active = True
        admin_user.approval_status = "approved"
        changed_password = not verify_password(password, admin_user.hashed_password)
        if changed_password:
            admin_user.hashed_password = hash_password(password)
            admin_user.token_version += 1
            admin_user.failed_login_attempts = 0
            admin_user.locked_until = None
        db.commit()
        logger.info("Bootstrap Admin reconciled (user_id=%s, password_updated=%s).", admin_user.id, changed_password)
        return

    db.add(User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        full_name="System Administrator",
        role_id=admin_role.id,
        is_active=True,
        approval_status="approved"
    ))
    db.commit()
    logger.info("Bootstrap Admin account created (username=%s).", username)


def initialize_application_data(db: Session) -> None:
    """Seed roles and baseline records at application startup, idempotently."""
    seed_roles(db)
    seed_users(db)
    seed_settings(db)
    seed_categories(db)


def seed_settings(db: Session):
    """Create default settings"""
    settings = [
        Setting(key="company_name", value="ESR Foods", description="Company name"),
        Setting(key="company_address", value="123 Fish Market Road, Chennai", description="Company address"),
        Setting(key="company_phone", value="+91 9876543210", description="Company phone"),
        Setting(key="company_email", value="info@esrfoods.com", description="Company email"),
        Setting(key="gst_number", value="33AABCU9603R1ZN", description="Company GST number"),
        Setting(key="invoice_prefix", value="ESR-INV", description="Invoice number prefix"),
        Setting(key="billing_cycle", value="15", description="Default billing cycle in days"),
        Setting(key="currency", value="INR", description="Default currency"),
        Setting(key="tax_rate", value="18", description="Default tax rate percentage"),
        Setting(key="low_stock_threshold", value="20", description="Low stock warning threshold"),
        Setting(key="expiry_warning_days", value="7", description="Days before expiry to warn"),
    ]
    
    for setting in settings:
        if not db.query(Setting).filter(Setting.key == setting.key).first():
            db.add(setting)
    
    db.commit()
    logger.info("Default application settings verified/seeded.")


def main():
    """Main function to seed default data"""
    print("Starting database initialization...")
    
    # Initialize database
    init_db()
    
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_users(db)
        seed_settings(db)
        seed_categories(db)
        
        print("\nDatabase initialization completed successfully!")
        print("\nAdministrator credentials are read from ADMIN_EMAIL and ADMIN_PASSWORD (or legacy ESR_ADMIN_* variables).")
        print("\nNote: All other data (products, vendors, restaurants, etc.) should be added through the application interface.")
        
    except Exception as e:
        db.rollback()
        print(f"\nError during initialization: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
