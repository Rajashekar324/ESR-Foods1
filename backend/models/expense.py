"""
Expense model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from backend.database import Base
import enum


class ExpenseCategory(str, enum.Enum):
    TRANSPORT = "transport"
    TRANSPORTATION = "transportation"
    UTILITIES = "utilities"
    ELECTRICITY = "electricity"
    COLD_STORAGE = "cold_storage"
    PACKAGING = "packaging"
    SUPPLIES = "supplies"
    SALARIES = "salaries"
    FUEL = "fuel"
    MAINTENANCE = "maintenance"
    ICE = "ice"
    RENT = "rent"
    OTHER = "other"
    MISCELLANEOUS = "miscellaneous"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    expense_code = Column(String(50), unique=True, nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    category = Column(SQLEnum(ExpenseCategory), nullable=False)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
