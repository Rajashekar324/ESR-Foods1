"""
API Routers for ESR Foods
"""
from backend.routers.auth import router as auth_router
from backend.routers.products import router as products_router
from backend.routers.inventory import router as inventory_router
from backend.routers.vendors import router as vendors_router
from backend.routers.purchases import router as purchases_router
from backend.routers.restaurants import router as restaurants_router
from backend.routers.customers import router as customers_router
from backend.routers.orders import router as orders_router
from backend.routers.invoices import router as invoices_router
from backend.routers.payments import router as payments_router
from backend.routers.expenses import router as expenses_router
from backend.routers.reports import router as reports_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.users import router as users_router
from backend.routers.notifications import router as notifications_router
from backend.routers.settings import router as settings_router

__all__ = [
    'auth_router',
    'products_router',
    'inventory_router',
    'vendors_router',
    'purchases_router',
    'restaurants_router',
    'customers_router',
    'orders_router',
    'invoices_router',
    'payments_router',
    'expenses_router',
    'reports_router',
    'dashboard_router',
    'users_router',
    'notifications_router',
    'settings_router'
]
