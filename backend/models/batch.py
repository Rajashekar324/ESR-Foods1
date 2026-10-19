"""
Product Batch model for batch-level inventory tracking
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class BatchStatus(str, enum.Enum):
    NORMAL = "normal"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    purchase_date = Column(DateTime(timezone=True), nullable=False)
    received_date = Column(DateTime(timezone=True), nullable=False)
    quantity = Column(Float, nullable=False)
    remaining_quantity = Column(Float, nullable=False)
    purchase_rate = Column(Float, nullable=False)
    manufacturing_date = Column(DateTime(timezone=True))
    expiry_date = Column(DateTime(timezone=True))
    storage_location = Column(String(100))
    status = Column(SQLEnum(BatchStatus), default=BatchStatus.NORMAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    product = relationship("Product", back_populates="batches")
    vendor = relationship("Vendor", back_populates="batches")
