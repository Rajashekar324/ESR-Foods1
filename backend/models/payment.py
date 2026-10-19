"""
Payment model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    CHEQUE = "cheque"
    OTHER = "other"


class PaymentType(str, enum.Enum):
    RECEIPT = "receipt"  # From restaurant/customer
    PAYMENT = "payment"  # To vendor


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REVERSED = "reversed"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_code = Column(String(50), unique=True, nullable=False, index=True)
    payment_type = Column(SQLEnum(PaymentType), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    status = Column(String(20), default="completed", nullable=False)
    transaction_reference = Column(String(100))
    notes = Column(Text)
    category = Column(String(50), nullable=True)
    paid_to = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    invoice = relationship("Invoice", back_populates="payments")
    purchase = relationship("Purchase")
    expense = relationship("Expense")
    restaurant = relationship("Restaurant", back_populates="payments")
