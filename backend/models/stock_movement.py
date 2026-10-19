"""
Stock Movement model for tracking all inventory changes
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class MovementType(str, enum.Enum):
    PURCHASE_RECEIVED = "purchase_received"
    CUSTOMER_RETURN = "customer_return"
    STOCK_ADJUSTMENT_IN = "stock_adjustment_in"
    RESTAURANT_SALE = "restaurant_sale"
    RETAIL_SALE = "retail_sale"
    DAMAGED_STOCK = "damaged_stock"
    EXPIRED_STOCK = "expired_stock"
    STOCK_ADJUSTMENT_OUT = "stock_adjustment_out"
    VENDOR_RETURN = "vendor_return"


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type = Column(SQLEnum(MovementType), nullable=False)
    reference_id = Column(Integer)  # Can reference purchase, order, etc.
    reference_type = Column(String(50))  # purchase, order, adjustment, etc.
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    rate = Column(Float)
    total = Column(Float)
    balance_after = Column(Float, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="stock_movements")
