from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
from app.services.logging import logging_service

router = APIRouter(prefix="/equipments", tags=["equipments"])


@router.get("", response_model=EquipmentList)
async def get_equipment_list(
    request: Request,
    include_disabled: bool = Query(False, description="是否包含停用的器材", alias="include_disabled"),
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取器材列表
    """
    # 記錄查詢操作
    await logging_service.audit(
        db,
        component="equipment",
        action="read",
        user_id=current_user.id,
        resource_type="equipments",
        resource_id="list",
        details={"include_disabled": include_disabled},
        ip_address=await logging_service.get_request_ip(request)
    )
    
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
    request: Request,
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
        # 記錄創建失敗
        await logging_service.warning(
            db,
            component="equipment",
            message=f"創建器材失敗：名稱 '{equipment_in.equipmentName}' 已存在",
            details={"equipmentName": equipment_in.equipmentName},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
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
    
    # 記錄創建成功
    await logging_service.audit(
        db,
        component="equipment",
        action="create",
        user_id=current_user.id,
        resource_type="equipment",
        resource_id=equipment.id,
        details={
            "equipmentName": equipment.name,
            "description": equipment.description,
            "enabled": equipment.enabled
        },
        ip_address=await logging_service.get_request_ip(request)
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
    request: Request,
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
        # 記錄更新失敗
        await logging_service.warning(
            db,
            component="equipment",
            message=f"更新器材失敗：ID '{equipment_id}' 不存在",
            details={"equipmentId": equipment_id, "equipmentName": equipment_in.equipmentName},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "器材不存在"}}
        )

    # 記錄原始值以便比較
    old_values = {
        "name": equipment.name,
        "description": equipment.description,
        "enabled": equipment.enabled
    }
    
    # 更新器材
    updated_equipment = await crud_equipment.update(db, db_obj=equipment, obj_in=equipment_in)
    if not updated_equipment:
        # 記錄更新失敗
        await logging_service.warning(
            db,
            component="equipment",
            message=f"更新器材失敗：名稱 '{equipment_in.equipmentName}' 已存在",
            details={
                "equipmentId": equipment_id,
                "currentName": equipment.name,
                "newName": equipment_in.equipmentName
            },
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "error": {"code": "DUPLICATE_RESOURCE", "message": "相同名稱的器材已存在"}}
        )
    
    # 記錄更新成功
    await logging_service.audit(
        db,
        component="equipment",
        action="update",
        user_id=current_user.id,
        resource_type="equipment",
        resource_id=equipment_id,
        details={
            "old": old_values,
            "new": {
                "name": updated_equipment.name,
                "description": updated_equipment.description,
                "enabled": updated_equipment.enabled
            }
        },
        ip_address=await logging_service.get_request_ip(request)
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
    request: Request,
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
        # 記錄狀態變更失敗
        await logging_service.warning(
            db,
            component="equipment",
            message=f"切換器材狀態失敗：ID '{equipment_id}' 不存在",
            details={"equipmentId": equipment_id, "enabled": status_in.enabled},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "器材不存在"}}
        )

    # 記錄原始狀態以便比較
    old_status = equipment.enabled
    action = "啟用" if status_in.enabled else "停用"
    
    # 如果是停用器材，需要檢查是否有未完成的申請
    if not status_in.enabled and equipment.enabled:
        can_disable = await crud_equipment.check_can_delete(db, equipment_id=equipment_id)
        if not can_disable:
            related_requests = await crud_equipment.get_related_requests(db, equipment_id=equipment_id)
            
            # 記錄狀態變更失敗
            await logging_service.warning(
                db,
                component="equipment",
                message=f"停用器材失敗：器材 '{equipment.name}' 已有待處理申請",
                details={
                    "equipmentId": equipment_id,
                    "equipmentName": equipment.name,
                    "relatedRequests": related_requests
                },
                user_id=current_user.id,
                ip_address=await logging_service.get_request_ip(request)
            )
            
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
    
    # 記錄狀態變更成功
    await logging_service.audit(
        db,
        component="equipment",
        action="update_status",
        user_id=current_user.id,
        resource_type="equipment",
        resource_id=equipment_id,
        details={
            "equipmentName": equipment.name,
            "oldStatus": old_status,
            "newStatus": equipment.enabled,
            "action": action
        },
        ip_address=await logging_service.get_request_ip(request)
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


@router.delete("/{equipment_id}", response_model=EquipmentDeleteResponse)
async def delete_equipment(
    request: Request,
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
        # 記錄刪除失敗
        await logging_service.warning(
            db,
            component="equipment",
            message=f"刪除器材失敗：ID '{equipment_id}' 不存在",
            details={"equipmentId": equipment_id},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "器材不存在"}}
        )

    # 記錄器材名稱，以便在刪除後仍保留在日誌中
    equipment_name = equipment.name
    
    # 檢查是否有關聯的未完成申請
    can_delete = await crud_equipment.check_can_delete(db, equipment_id=equipment_id)
    if not can_delete:
        related_requests = await crud_equipment.get_related_requests(db, equipment_id=equipment_id)
        
        # 記錄刪除失敗
        await logging_service.warning(
            db,
            component="equipment",
            message=f"刪除器材失敗：器材 '{equipment_name}' 仍有關聯的未完成申請",
            details={
                "equipmentId": equipment_id,
                "equipmentName": equipment_name,
                "relatedRequests": related_requests
            },
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
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
    
    # 記錄刪除成功
    await logging_service.audit(
        db,
        component="equipment",
        action="delete",
        user_id=current_user.id,
        resource_type="equipment",
        resource_id=equipment_id,
        details={
            "equipmentId": equipment_id,
            "equipmentName": equipment_name
        },
        ip_address=await logging_service.get_request_ip(request)
    )

    return {
        "success": True,
        "data": {
            "equipmentId": equipment_id,
            "deleted": True,
        }
    }