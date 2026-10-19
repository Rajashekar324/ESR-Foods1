"""
Settings router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models.setting import Setting
from backend.schemas.setting import SettingCreate, SettingResponse
from backend.auth.security import require_admin

router = APIRouter(prefix="/api/settings", tags=["Settings"], dependencies=[Depends(require_admin())])


@router.post("/", response_model=SettingResponse)
async def create_setting(
    setting_data: SettingCreate,
    current_user = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new setting (Manager/Admin only)
    """
    if db.query(Setting).filter(Setting.key == setting_data.key).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setting key already exists"
        )
    
    new_setting = Setting(**setting_data.model_dump())
    db.add(new_setting)
    db.commit()
    db.refresh(new_setting)
    
    return new_setting


@router.get("/", response_model=List[SettingResponse])
async def get_settings(
    current_user = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Get all settings
    """
    settings = db.query(Setting).all()
    return settings


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    current_user = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Get a specific setting by key
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    return setting


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    value: str,
    current_user = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Update a setting (Manager/Admin only)
    """
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    setting.value = value
    db.commit()
    db.refresh(setting)
    
    return setting


@router.post("/reset-database")
async def reset_database(
    current_user = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Clear all business data and reseed defaults (Admin only)
    """
    from backend.clear_data import clear_all_business_data
    try:
        clear_all_business_data()
        return {"message": "All data cleared and default categories reseeded successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {str(e)}"
        )

