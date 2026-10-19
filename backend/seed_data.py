"""
Seed data script for ESR Foods
Run this to initialize the database with default roles and admin user
"""
import sys
import os
import secrets
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from backend.database import SessionLocal, init_db
from backend.models.user import User, Role
from backend.models.setting import Setting
from backend.models.product import Category
from backend.auth.security import hash_password, verify_password


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
    print("Categories seeded")


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
    print("Roles seeded")


def seed_users(db: Session):
    """Ensure one active Admin exists and securely bootstrap it if needed."""
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    username = os.getenv("ESR_ADMIN_USERNAME", "admin")
    active_admin = db.query(User).join(Role).filter(
        Role.name == "admin", User.is_active.is_(True), User.approval_status == "approved"
    ).first()
    if active_admin:
        configured_password = os.getenv("ESR_ADMIN_PASSWORD")
        if active_admin.username == username and configured_password:
            validate_password(configured_password)
            if verify_password("admin123", active_admin.hashed_password) and not verify_password(configured_password, active_admin.hashed_password):
                active_admin.hashed_password = hash_password(configured_password)
                active_admin.token_version += 1
                db.commit()
                print("Legacy default Admin password replaced with ESR_ADMIN_PASSWORD.")
                return None
        if active_admin.username == username and configured_password and not verify_password(configured_password, active_admin.hashed_password):
            active_admin.hashed_password = hash_password(configured_password)
            active_admin.token_version += 1
            db.commit()
            print("Active Admin password updated from ESR_ADMIN_PASSWORD.")
            return None
        if active_admin.username == username and verify_password("admin123", active_admin.hashed_password):
            password = secrets.token_urlsafe(24) + "A9!"
            active_admin.hashed_password = hash_password(password)
            active_admin.token_version += 1
            db.commit()
            print("Legacy default Admin password has been rotated.")
            return password
        print("An active Admin account already exists; credentials were not changed.")
        return None

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        if existing_user.role.name != "admin":
            raise RuntimeError("Configured ESR_ADMIN_USERNAME belongs to a non-admin account.")
        existing_user.is_active = True
        existing_user.approval_status = "approved"
        existing_user.token_version += 1
        db.commit()
        print("Existing administrator account re-enabled; password was not changed.")
        return None

    configured_password = os.getenv("ESR_ADMIN_PASSWORD")
    password = configured_password or (secrets.token_urlsafe(24) + "A9!")
    validate_password(password)
    db.add(User(
        username=username,
        email=os.getenv("ESR_ADMIN_EMAIL", "admin@esrfoods.com"),
        hashed_password=hash_password(password),
        full_name="System Administrator",
        role_id=admin_role.id,
        is_active=True,
        approval_status="approved"
    ))
    db.commit()
    print("Admin user seeded")
    return password if not configured_password else None


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
    print("Settings seeded")


def main():
    """Main function to seed default data"""
    print("Starting database initialization...")
    
    # Initialize database
    init_db()
    
    db = SessionLocal()
    try:
        seed_roles(db)
        generated_admin_password = seed_users(db)
        seed_settings(db)
        seed_categories(db)
        
        print("\nDatabase initialization completed successfully!")
        print("\nAdministrator login:")
        print(f"  Username: {os.getenv('ESR_ADMIN_USERNAME', 'admin')}")
        if generated_admin_password:
            print(f"  One-time generated password: {generated_admin_password}")
        print("\nNote: All other data (products, vendors, restaurants, etc.) should be added through the application interface.")
        
    except Exception as e:
        db.rollback()
        print(f"\nError during initialization: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
