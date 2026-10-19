"""
Main FastAPI application for ESR Foods
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

from backend.database import get_db, init_db
from backend.auth.security import get_current_page_user, require_admin_page, require_manager_page
from backend.routers import (
    auth_router,
    products_router,
    inventory_router,
    vendors_router,
    purchases_router,
    restaurants_router,
    customers_router,
    orders_router,
    invoices_router,
    payments_router,
    expenses_router,
    reports_router,
    dashboard_router,
    users_router,
    notifications_router,
    settings_router
)

# Create FastAPI app
app = FastAPI(
    title="ESR Foods Business Operations Management System",
    description="Complete ERP/CRM system for seafood distribution business",
    version="1.0.0"
)

TRUSTED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if origin.strip()
]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=TRUSTED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def validate_cookie_request_origin(request, call_next):
    """Reject cross-origin unsafe requests that would use ambient session cookies."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get("esr_session"):
        origin = request.headers.get("origin")
        allowed = set(TRUSTED_ORIGINS)
        request_origin = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
        allowed.add(request_origin)
        normalized_origin = origin.rstrip("/") if origin else None
        if normalized_origin not in allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"detail": "Request origin validation failed"})
    return await call_next(request)

# Include routers
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(vendors_router)
app.include_router(purchases_router)
app.include_router(restaurants_router)
app.include_router(customers_router)
app.include_router(orders_router)
app.include_router(invoices_router)
app.include_router(payments_router)
app.include_router(expenses_router)
app.include_router(reports_router)
app.include_router(dashboard_router)
app.include_router(users_router)
app.include_router(notifications_router)
app.include_router(settings_router)

# Mount static files
static_dir = str(PROJECT_ROOT / "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount frontend directory to serve CSS and JS files
frontend_dir = str(PROJECT_ROOT / "frontend")
if os.path.exists(frontend_dir):
    app.mount("/frontend/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="frontend-css")
    app.mount("/frontend/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="frontend-js")

# Serve frontend
@app.get("/")
async def serve_frontend():
    """Serve the frontend login page"""
    frontend_path = PROJECT_ROOT / "frontend" / "login.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "ESR Foods API - Frontend not found. Please build the frontend first."}


# Serve specific frontend pages
@app.get("/login.html")
async def serve_login():
    frontend_path = PROJECT_ROOT / "frontend" / "login.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/dashboard.html", dependencies=[Depends(require_manager_page())])
async def serve_dashboard():
    frontend_path = PROJECT_ROOT / "frontend" / "dashboard.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/products.html", dependencies=[Depends(require_manager_page())])
async def serve_products():
    frontend_path = PROJECT_ROOT / "frontend" / "products.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/inventory.html", dependencies=[Depends(require_manager_page())])
async def serve_inventory():
    frontend_path = PROJECT_ROOT / "frontend" / "inventory.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/vendors.html", dependencies=[Depends(require_manager_page())])
async def serve_vendors():
    frontend_path = PROJECT_ROOT / "frontend" / "vendors.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/purchases.html", dependencies=[Depends(require_manager_page())])
async def serve_purchases():
    frontend_path = PROJECT_ROOT / "frontend" / "purchases.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/restaurants.html", dependencies=[Depends(require_manager_page())])
async def serve_restaurants():
    frontend_path = PROJECT_ROOT / "frontend" / "restaurants.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/customers.html", dependencies=[Depends(require_manager_page())])
async def serve_customers():
    frontend_path = PROJECT_ROOT / "frontend" / "customers.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/orders.html", dependencies=[Depends(require_manager_page())])
async def serve_orders():
    frontend_path = PROJECT_ROOT / "frontend" / "orders.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/invoices.html", dependencies=[Depends(require_manager_page())])
async def serve_invoices():
    frontend_path = PROJECT_ROOT / "frontend" / "invoices.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/payments.html", dependencies=[Depends(require_manager_page())])
async def serve_payments():
    frontend_path = PROJECT_ROOT / "frontend" / "payments.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/expenses.html", dependencies=[Depends(require_manager_page())])
async def serve_expenses():
    frontend_path = PROJECT_ROOT / "frontend" / "expenses.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/reports.html", dependencies=[Depends(require_manager_page())])
async def serve_reports():
    frontend_path = PROJECT_ROOT / "frontend" / "reports.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/notifications.html", dependencies=[Depends(get_current_page_user)])
async def serve_notifications():
    frontend_path = PROJECT_ROOT / "frontend" / "notifications.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/users.html", dependencies=[Depends(require_admin_page())])
async def serve_users():
    frontend_path = PROJECT_ROOT / "frontend" / "users.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.get("/settings.html", dependencies=[Depends(require_admin_page())])
async def serve_settings():
    frontend_path = PROJECT_ROOT / "frontend" / "settings.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Page not found"}


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Report healthy only when the database is reachable."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from exc
    return {"status": "healthy", "message": "ESR Foods API and database are available"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
