"""
Invoice and InvoiceItem models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True))
    subtotal = Column(Float, default=0)
    discount = Column(Float, default=0)
    tax = Column(Float, default=0)
    grand_total = Column(Float, default=0)
    amount_paid = Column(Float, default=0)
    balance_due = Column(Float, default=0)
    payment_status = Column(String(50), default="unpaid")
    notes = Column(Text)
    is_finalized = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    restaurant = relationship("Restaurant", back_populates="invoices")
    order = relationship("SalesOrder", back_populates="invoice")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    rate = Column(Float, nullable=False)
    discount = Column(Float, default=0)
    tax = Column(Float, default=0)
    amount = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")
