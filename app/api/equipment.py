from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_academic_staff_user, get_applicant_user
from app.database import get_db
from app.models.users import User
from app.crud.equipment import equipment as crud_equipment
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    EquipmentList,
    EquipmentToggleStatus,
    EquipmentToggleStatusResponse,
    EquipmentDeleteResponse,
)

router = APIRouter(prefix="/equipments", tags=["equipments"])


@router.get("", response_model=EquipmentList)
async def get_equipment_list(
    include_disabled: bool = Query(False, description="是否包含停用的器材", alias="include_disabled"),
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取器材列表
    """
    equipment_list = await crud_equipment.get_all(db, include_disabled=include_disabled)
    
    # 轉換為回應格式
    equipment_response = []
    for e in equipment_list:
        equipment_response.append({
            "equipmentId": e.id,
            "equipmentName": e.name,
            "description": e.description,
            "enabled": e.enabled,
            "createdAt": e.created_at,
            "updatedAt": e.updated_at,
        })
    
    return {"success": True, "data": {"equipments": equipment_response}}


@router.post("", response_model=EquipmentResponse)
async def create_equipment(
    equipment_in: EquipmentCreate,
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    創建新器材
    """
    # 檢查名稱是否已存在
    existing = await crud_equipment.get_by_name(db, name=equipment_in.equipmentName)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "error": {"code": "DUPLICATE_RESOURCE", "message": "相同名稱的器材已存在"}}
        )
    
    # 創建器材
    equipment = await crud_equipment.create(
        db, 
        obj_in=equipment_in, 
        created_by=current_user.id
    )
    
    return {
        "success": True,
        "data": {
            "equipmentId": equipment.id,
            "equipmentName": equipment.name,
            "description": equipment.description,
            "enabled": equipment.enabled,
            "createdAt": equipment.created_at,
            "updatedAt": equipment.updated_at,
        }
    }


@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: str,
    equipment_in: EquipmentUpdate,
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    更新器材資訊
    """
    # 檢查器材是否存在
    equipment = await crud_equipment.get(db, id=equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "器材不存在"}}
        )
    
    # 更新器材
    updated_equipment = await crud_equipment.update(db, db_obj=equipment, obj_in=equipment_in)
    if not updated_equipment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "error": {"code": "DUPLICATE_RESOURCE", "message": "相同名稱的器材已存在"}}
        )
    
    return {
        "success": True,
        "data": {
            "equipmentId": updated_equipment.id,
            "equipmentName": updated_equipment.name,
            "description": updated_equipment.description,
            "enabled": updated_equipment.enabled,
            "createdAt": updated_equipment.created_at,
            "updatedAt": updated_equipment.updated_at,
        }
    }


@router.patch("/{equipment_id}/toggle-status", response_model=EquipmentToggleStatusResponse)
async def toggle_equipment_status(
    equipment_id: str,
    status_in: EquipmentToggleStatus,
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    啟用/停用器材
    """
    # 檢查器材是否存在
    equipment = await crud_equipment.get(db, id=equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "器材不存在"}}
        )
    
    # 如果是停用器材，需要檢查是否有未完成的申請
    if not status_in.enabled and equipment.enabled:
        can_disable = await crud_equipment.check_can_delete(db, equipment_id=equipment_id)
        if not can_disable:
            related_requests = await crud_equipment.get_related_requests(db, equipment_id=equipment_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "error": {
                        "code": "RESOURCE_IN_USE",
                        "message": "無法停用已有待處理申請的器材",
                        "details": {"relatedRequests": related_requests}
                    }
                }
            )
    
    # 更新狀態
    equipment = await crud_equipment.toggle_status(db, db_obj=equipment, enabled=status_in.enabled)
    
    return {
        "success": True,
        "data": {
            "equipmentId": equipment.id,
            "equipmentName": equipment.name,
            "description": equipment.description,
            "enabled": equipment.enabled,
            "createdAt": equipment.created_at,
            "updatedAt": equipment.updated_at,
        }
    }


@router.delete("/{equipment_id}", response_model=EquipmentDeleteResponse)
async def delete_equipment(
    equipment_id: str,
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    刪除器材
    """
    # 檢查器材是否存在
    equipment = await crud_equipment.get(db, id=equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "器材不存在"}}
        )
    
    # 檢查是否有關聯的未完成申請
    can_delete = await crud_equipment.check_can_delete(db, equipment_id=equipment_id)
    if not can_delete:
        related_requests = await crud_equipment.get_related_requests(db, equipment_id=equipment_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "error": {
                    "code": "RESOURCE_IN_USE",
                    "message": "器材仍有關聯的未完成申請，無法刪除",
                    "details": {"relatedRequests": related_requests}
                }
            }
        )
    
    # 刪除器材
    await crud_equipment.remove(db, id=equipment_id)
    
    return {
        "success": True,
        "data": {
            "equipmentId": equipment_id,
            "deleted": True,
        }
    }