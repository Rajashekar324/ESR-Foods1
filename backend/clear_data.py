"""
Clear business data script for ESR Foods
This script clears all transactional and master business data (products, sales, purchases, customers, vendors, etc.)
while preserving user accounts, roles, settings, and reseeding clean default categories.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine, Base
from backend.models import (
    AuditLog, Notification, StockMovement, ProductBatch, Expense, Payment,
    InvoiceItem, Invoice, SalesOrderItem, SalesOrder, PurchaseItem, Purchase,
    RetailCustomer, RestaurantNote, Restaurant, Vendor, Product, Category
)
from backend.seed_data import seed_categories, seed_roles, seed_users, seed_settings


def clear_all_business_data():
    """Clear all business data tables in reverse foreign key dependency order"""
    db = SessionLocal()
    try:
        print("Clearing business data...")
        
        db.query(AuditLog).delete()
        db.query(Notification).delete()
        db.query(StockMovement).delete()
        db.query(ProductBatch).delete()
        db.query(Expense).delete()
        db.query(Payment).delete()
        db.query(InvoiceItem).delete()
        db.query(Invoice).delete()
        db.query(SalesOrderItem).delete()
        db.query(SalesOrder).delete()
        db.query(PurchaseItem).delete()
        db.query(Purchase).delete()
        db.query(RetailCustomer).delete()
        db.query(RestaurantNote).delete()
        db.query(Restaurant).delete()
        db.query(Vendor).delete()
        db.query(Product).delete()
        db.query(Category).delete()
        
        db.commit()
        print("All business data cleared successfully.")
        
        # Reseed initial setup (roles, admin user, settings, categories)
        seed_roles(db)
        seed_users(db)
        seed_settings(db)
        seed_categories(db)
        
        print("Default roles, settings, and categories re-seeded successfully.")
        
    except Exception as e:
        print(f"Error clearing business data: {e}")
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    clear_all_business_data()
