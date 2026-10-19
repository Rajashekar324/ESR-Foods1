"""
Purchase and PurchaseItem models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class PurchaseStatus(str, enum.Enum):
    DRAFT = "draft"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    purchase_code = Column(String(50), unique=True, nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    vendor_invoice_number = Column(String(100))
    purchase_date = Column(DateTime(timezone=True), nullable=False)
    expected_date = Column(DateTime(timezone=True))
    received_date = Column(DateTime(timezone=True))
    subtotal = Column(Float, default=0)
    discount = Column(Float, default=0)
    tax = Column(Float, default=0)
    total = Column(Float, default=0)
    payment_status = Column(String(50), default="unpaid")
    status = Column(SQLEnum(PurchaseStatus), default=PurchaseStatus.DRAFT)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    rate = Column(Float, nullable=False)
    discount = Column(Float, default=0)
    tax = Column(Float, default=0)
    total = Column(Float, nullable=False)

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product")
