"""
Dashboard schemas
"""
from pydantic import BaseModel
from typing import List, Optional


class DashboardSummary(BaseModel):
    today_sales: float
    today_purchases: float
    monthly_sales: float
    outstanding_receivables: float
    outstanding_vendor_payables: float
    total_stock_value: float
    active_restaurants: int
    low_stock_products: int
    expiring_products: int


class DashboardCharts(BaseModel):
    sales_trend: List[dict]
    top_products: List[dict]
    top_restaurants: List[dict]
    inventory_distribution: List[dict]


class RestaurantBreakdown(BaseModel):
    restaurant_name: str
    orders: int
    sales: float
    collected: float
    outstanding: float


class FifteenDaySummary(BaseModel):
    period_start: str
    period_end: str
    total_sales: float
    total_collected: float
    total_outstanding: float
    collection_rate: float
    restaurant_breakdown: List[RestaurantBreakdown]
