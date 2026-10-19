"""
Audit Log model for tracking system activities
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # create, update, delete, login, etc.
    module = Column(String(50), nullable=False)  # products, restaurants, orders, etc.
    record_id = Column(Integer)
    previous_value = Column(Text)
    new_value = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
