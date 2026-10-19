"""
Vendor schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class VendorCreate(BaseModel):
    vendor_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    payment_terms: Optional[str] = None
    bank_details: Optional[str] = None
    notes: Optional[str] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    payment_terms: Optional[str] = None
    bank_details: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[bool] = None


class VendorResponse(BaseModel):
    id: int
    vendor_code: str
    name: str
    company_name: Optional[str]
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    gst_number: Optional[str]
    payment_terms: Optional[str]
    bank_details: Optional[str]
    notes: Optional[str]
    status: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
