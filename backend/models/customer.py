"""
Customer models
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class RetailCustomer(Base):
    __tablename__ = "retail_customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(Text)
    total_purchases = Column(Float, default=0)
    last_purchase_date = Column(DateTime(timezone=True))
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    orders = relationship("SalesOrder", back_populates="customer")
