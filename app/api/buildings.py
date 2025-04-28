from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Request
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
from app.services.logging import logging_service

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("", response_model=BuildingList)
async def get_buildings(
    request: Request,
    include_disabled: bool = Query(False, description="是否包含停用的大樓"),
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取大樓列表
    """
    # 記錄查詢操作
    await logging_service.audit(
        db,
        component="building",
        action="read",
        user_id=current_user.id,
        resource_type="buildings",
        resource_id="list",
        details={"include_disabled": include_disabled},
        ip_address=await logging_service.get_request_ip(request)
    )
    
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
    request: Request,
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
        # 記錄創建失敗
        await logging_service.warning(
            db,
            component="building",
            message=f"創建大樓失敗：名稱 '{building_in.buildingName}' 已存在",
            details={"buildingName": building_in.buildingName},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "error": {"code": "DUPLICATE_RESOURCE", "message": "大樓名稱已存在"}}
        )

    # 創建大樓
    building = await crud_building.create(db, obj_in=building_in, created_by=current_user.id)
    
    # 記錄創建成功
    await logging_service.audit(
        db,
        component="building",
        action="create",
        user_id=current_user.id,
        resource_type="building",
        resource_id=building.id,
        details={
            "buildingName": building.name,
            "enabled": building.enabled
        },
        ip_address=await logging_service.get_request_ip(request)
    )

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
    request: Request,
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
        # 記錄更新失敗
        await logging_service.warning(
            db,
            component="building",
            message=f"更新大樓失敗：ID '{building_id}' 不存在",
            details={"buildingId": building_id, "buildingName": building_in.buildingName},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "大樓不存在"}}
        )

    # 記錄原始值以便比較
    old_name = building.name
    
    # 檢查名稱是否已存在
    if building_in.buildingName != building.name:
        existing = await crud_building.get_by_name(db, name=building_in.buildingName)
        if existing:
            # 記錄更新失敗
            await logging_service.warning(
                db,
                component="building",
                message=f"更新大樓失敗：名稱 '{building_in.buildingName}' 已存在",
                details={
                    "buildingId": building_id,
                    "currentName": building.name,
                    "newName": building_in.buildingName
                },
                user_id=current_user.id,
                ip_address=await logging_service.get_request_ip(request)
            )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"success": False, "error": {"code": "DUPLICATE_RESOURCE", "message": "大樓名稱已存在"}}
            )

    # 更新大樓
    building = await crud_building.update_name(db, db_obj=building, name=building_in.buildingName)
    
    # 記錄更新成功
    await logging_service.audit(
        db,
        component="building",
        action="update",
        user_id=current_user.id,
        resource_type="building",
        resource_id=building_id,
        details={
            "oldName": old_name,
            "newName": building.name
        },
        ip_address=await logging_service.get_request_ip(request)
    )

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
    request: Request,
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
        # 記錄更新失敗
        await logging_service.warning(
            db,
            component="building",
            message=f"切換大樓狀態失敗：ID '{building_id}' 不存在",
            details={"buildingId": building_id, "enabled": status_in.enabled},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "大樓不存在"}}
        )

    # 記錄原始狀態以便比較
    old_status = building.enabled
    action = "啟用" if status_in.enabled else "停用"
    
    # 更新狀態
    building = await crud_building.toggle_status(db, db_obj=building, enabled=status_in.enabled)
    
    # 記錄狀態變更
    await logging_service.audit(
        db,
        component="building",
        action="update_status",
        user_id=current_user.id,
        resource_type="building",
        resource_id=building_id,
        details={
            "buildingName": building.name,
            "oldStatus": old_status,
            "newStatus": building.enabled,
            "action": action
        },
        ip_address=await logging_service.get_request_ip(request)
    )

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
    request: Request,
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
        # 記錄刪除失敗
        await logging_service.warning(
            db,
            component="building",
            message=f"刪除大樓失敗：ID '{building_id}' 不存在",
            details={"buildingId": building_id},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": {"code": "NOT_FOUND", "message": "大樓不存在"}}
        )

    # 記錄大樓名稱，以便在刪除後仍保留在日誌中
    building_name = building.name
    
    # 檢查是否有關聯的未完成申請
    can_delete = await crud_building.check_can_delete(db, building_id=building_id)
    if not can_delete:
        related_requests = await crud_building.get_related_requests(db, building_id=building_id)
        
        # 記錄刪除失敗
        await logging_service.warning(
            db,
            component="building",
            message=f"刪除大樓失敗：大樓 '{building_name}' 仍有關聯的未完成申請",
            details={
                "buildingId": building_id,
                "buildingName": building_name,
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
                    "message": "大樓仍有關聯的未完成申請，無法刪除",
                    "details": {"relatedRequests": related_requests}
                }
            }
        )

    # 刪除大樓
    await crud_building.remove(db, id=building_id)
    
    # 記錄刪除成功
    await logging_service.audit(
        db,
        component="building",
        action="delete",
        user_id=current_user.id,
        resource_type="building",
        resource_id=building_id,
        details={
            "buildingId": building_id,
            "buildingName": building_name
        },
        ip_address=await logging_service.get_request_ip(request)
    )

    return {
        "success": True,
        "data": {
            "buildingId": building_id,
            "deleted": True,
        }
    }