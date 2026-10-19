"""
Vendor model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    vendor_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    company_name = Column(String(200))
    contact_person = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(Text)
    gst_number = Column(String(50))
    payment_terms = Column(String(255))
    bank_details = Column(Text)
    notes = Column(Text)
    credit_adjustments = Column(Float, default=0, nullable=False)
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    purchases = relationship("Purchase", back_populates="vendor")
    batches = relationship("ProductBatch", back_populates="vendor")
