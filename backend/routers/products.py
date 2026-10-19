"""
Products router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db
from backend.models.product import Product, Category
from backend.models.user import User
from backend.schemas.product import ProductCreate, ProductUpdate, ProductResponse, CategoryCreate, CategoryResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin
from datetime import datetime

router = APIRouter(prefix="/api/products", tags=["Products"], dependencies=[Depends(require_manager_or_admin())])


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new product (Manager/Admin only)
    """
    # Check if product code exists
    if db.query(Product).filter(Product.product_code == product_data.product_code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product code already exists"
        )
    
    # Verify category if provided
    if product_data.category_id:
        category = db.query(Category).filter(Category.id == product_data.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category"
            )
    
    new_product = Product(**product_data.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return new_product


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    seafood_type: Optional[str] = None,
    status: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all products with optional filters
    """
    query = db.query(Product)
    
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.product_code.ilike(f"%{search}%")) |
            (Product.variety.ilike(f"%{search}%"))
        )
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if seafood_type:
        query = query.filter(Product.seafood_type == seafood_type)
    
    if status is not None:
        query = query.filter(Product.is_active == status)
    
    products = query.order_by(Product.name).offset(skip).limit(limit).all()
    return products


# Category endpoints (must be defined BEFORE /{product_id} to avoid matching conflict)
@router.get("/categories/", response_model=List[CategoryResponse])
@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all categories
    """
    return db.query(Category).order_by(Category.name).all()


@router.post("/categories/", response_model=CategoryResponse)
@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new category (Manager/Admin only)
    """
    if db.query(Category).filter(Category.name == category_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category name already exists"
        )
    
    new_category = Category(**category_data.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return new_category


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete a category (Manager/Admin only)
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific product by ID
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update a product (Manager/Admin only)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete a product (Manager/Admin only)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    db.delete(product)
    db.commit()
    
    return {"message": "Product deleted successfully"}

