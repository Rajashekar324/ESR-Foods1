"""
Product and Category models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class SeafoodType(str, enum.Enum):
    FISH = "fish"
    PRAWNS = "prawns"
    SHRIMP = "shrimp"
    CRAB = "crab"
    SQUID = "squid"
    OTHER = "other"


class UnitType(str, enum.Enum):
    KG = "kg"
    GRAM = "gram"
    BOX = "box"
    PACKET = "packet"
    PIECE = "piece"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    seafood_type = Column(SQLEnum(SeafoodType), nullable=False)
    variety = Column(String(100))
    brand = Column(String(100))
    grade = Column(String(50))
    size = Column(String(50))
    unit = Column(SQLEnum(UnitType), nullable=False)
    weight_per_packet = Column(Float)
    packaging_type = Column(String(100))
    is_frozen = Column(Boolean, default=True)
    purchase_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    wholesale_price = Column(Float)
    retail_price = Column(Float)
    current_stock = Column(Float, default=0)
    minimum_stock = Column(Float, default=10)
    maximum_stock = Column(Float)
    reorder_level = Column(Float, default=20)
    preferred_vendor_id = Column(Integer, ForeignKey("vendors.id"))
    storage_location = Column(String(100))
    manufacturing_date = Column(DateTime(timezone=True))
    expiry_info = Column(String(255))
    product_image = Column(String(500))
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    preferred_vendor = relationship("Vendor", foreign_keys=[preferred_vendor_id])
    batches = relationship("ProductBatch", back_populates="product")
    stock_movements = relationship("StockMovement", back_populates="product")

    @property
    def status(self):
        return self.is_active

    @status.setter
    def status(self, value):
        self.is_active = value
