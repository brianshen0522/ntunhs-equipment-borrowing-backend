from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_academic_staff_user
from app.database import get_db
from app.models.users import User
from app.crud.buildings import building as crud_building
from app.schemas.buildings import (
    BuildingCreate,
    BuildingUpdate,
    BuildingResponse,
    BuildingList,
    BuildingToggleStatus,
    BuildingToggleStatusResponse,
    BuildingDeleteResponse,
)

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("", response_model=BuildingList)
async def get_buildings(
    include_disabled: bool = Query(False, description="是否包含停用的大樓"),
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取大樓列表
    """
    buildings = await crud_building.get_all(db, include_disabled=include_disabled)
    
    # 轉換為回應格式
    buildings_list = []
    for b in buildings:
        buildings_list.append({
            "buildingId": b.id,
            "buildingName": b.name,
            "enabled": b.enabled,
            "createdAt": b.created_at,
        })
    
    return {"success": True, "data": {"buildings": buildings_list}}


@router.post("", response_model=BuildingResponse)
async def create_building(
    building_in: BuildingCreate,
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    創建新大樓
    """
    # 檢查名稱是否已存在
    existing = await crud_building.get_by_name(db, name=building_in.buildingName)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "error": {"code": "DUPLICATE_RESOURCE", "message": "大樓名稱已存在"}}
        )
    
    # 創建大樓
    building = await crud_building.create(db, obj_in=building_in, created_by=current_user.id)
    
    return {
        "success": True,
        "data": {
            "buildingId": building.id,
            "buildingName": building.name,
            "enabled": building.enabled,
            "createdAt": building.created_at,
        }
    }


@router.put("/{building_id}", response_model=BuildingResponse)
async def update_building(
    building_id: str,
    building_in: BuildingUpdate,
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    更新大樓資訊
    """
    # 檢查大樓是否存在
    building = await crud_building.get(db, id=building_id)
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "大樓不存在"}}
        )
    
    # 檢查名稱是否已存在
    if building_in.buildingName != building.name:
        existing = await crud_building.get_by_name(db, name=building_in.buildingName)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"success": False, "error": {"code": "DUPLICATE_RESOURCE", "message": "大樓名稱已存在"}}
            )
    
    # 更新大樓
    building = await crud_building.update_name(db, db_obj=building, name=building_in.buildingName)
    
    return {
        "success": True,
        "data": {
            "buildingId": building.id,
            "buildingName": building.name,
            "enabled": building.enabled,
            "createdAt": building.created_at,
        }
    }


@router.patch("/{building_id}/toggle-status", response_model=BuildingToggleStatusResponse)
async def toggle_building_status(
    building_id: str,
    status_in: BuildingToggleStatus,
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    啟用/停用大樓
    """
    # 檢查大樓是否存在
    building = await crud_building.get(db, id=building_id)
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "大樓不存在"}}
        )
    
    # 更新狀態
    building = await crud_building.toggle_status(db, db_obj=building, enabled=status_in.enabled)
    
    return {
        "success": True,
        "data": {
            "buildingId": building.id,
            "buildingName": building.name,
            "enabled": building.enabled,
            "createdAt": building.created_at,  # 確保包含這個字段
        }
    }


@router.delete("/{building_id}", response_model=BuildingDeleteResponse)
async def delete_building(
    building_id: str,
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    刪除大樓
    """
    # 檢查大樓是否存在
    building = await crud_building.get(db, id=building_id)
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "大樓不存在"}}
        )
    
    # 檢查是否有關聯的未完成申請
    can_delete = await crud_building.check_can_delete(db, building_id=building_id)
    if not can_delete:
        related_requests = await crud_building.get_related_requests(db, building_id=building_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "error": {
                    "code": "RESOURCE_IN_USE",
                    "message": "大樓仍有關聯的未完成申請，無法刪除",
                    "details": {"relatedRequests": related_requests}
                }
            }
        )
    
    # 刪除大樓
    await crud_building.remove(db, id=building_id)
    
    return {
        "success": True,
        "data": {
            "buildingId": building_id,
            "deleted": True,
        }
    }