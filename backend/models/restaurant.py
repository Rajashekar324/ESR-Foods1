"""
Restaurant and RestaurantNote models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class RestaurantType(str, enum.Enum):
    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    CLOUD_KITCHEN = "cloud_kitchen"
    CAFE = "cafe"
    CATERING = "catering"
    OTHER = "other"


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    restaurant_type = Column(SQLEnum(RestaurantType), nullable=False)
    owner_name = Column(String(100))
    contact_person = Column(String(100))
    phone = Column(String(20), nullable=False)
    whatsapp = Column(String(20))
    email = Column(String(100))
    address = Column(Text)
    area = Column(String(100))
    gst_number = Column(String(50))
    credit_limit = Column(Float, default=0)
    payment_terms = Column(String(255))
    assigned_salesperson = Column(String(100))
    status = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    orders = relationship("SalesOrder", back_populates="restaurant")
    invoices = relationship("Invoice", back_populates="restaurant")
    payments = relationship("Payment", back_populates="restaurant")
    restaurant_notes = relationship("RestaurantNote", back_populates="restaurant", cascade="all, delete-orphan")

    @property
    def is_active(self):
        return self.status

    @is_active.setter
    def is_active(self, value):
        self.status = value


class RestaurantNote(Base):
    __tablename__ = "restaurant_notes"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    note = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    restaurant = relationship("Restaurant", back_populates="restaurant_notes")
