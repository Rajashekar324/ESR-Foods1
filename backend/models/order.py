"""
Sales Order and SalesOrderItem models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    PACKED = "packed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CustomerType(str, enum.Enum):
    RESTAURANT = "restaurant"
    RETAIL = "retail"


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(50), unique=True, nullable=False, index=True)
    customer_type = Column(SQLEnum(CustomerType), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("retail_customers.id"), nullable=True)
    order_date = Column(DateTime(timezone=True), nullable=False)
    delivery_date = Column(DateTime(timezone=True))
    subtotal = Column(Float, default=0)
    discount = Column(Float, default=0)
    tax = Column(Float, default=0)
    total = Column(Float, default=0)
    payment_status = Column(String(50), default="unpaid")
    order_status = Column(SQLEnum(OrderStatus), default=OrderStatus.DRAFT)
    delivery_status = Column(SQLEnum(DeliveryStatus), default=DeliveryStatus.PENDING)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    restaurant = relationship("Restaurant", back_populates="orders")
    customer = relationship("RetailCustomer", back_populates="orders")
    items = relationship("SalesOrderItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="order", uselist=False)


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    selling_price = Column(Float, nullable=False)
    discount = Column(Float, default=0)
    tax = Column(Float, default=0)
    total = Column(Float, nullable=False)

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product")
