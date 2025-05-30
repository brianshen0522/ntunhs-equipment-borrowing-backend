from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_system_admin_user
from app.database import get_db
from app.models.users import User, UserRole
from app.core.auth import get_user_roles
from app.schemas.settings import (
    UserListParams,
    UserListResponse,
    UserRoleManage,
    UserRoleResponse,
)
from app.services.logging import logging_service

router = APIRouter(prefix="/admin/users", tags=["admin"])

@router.get("", response_model=UserListResponse)
async def get_users_list(
    request: Request,
    params: UserListParams = Depends(),
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取系統使用者列表（不限角色）
    """
    # 記錄查詢操作
    await logging_service.audit(
        db,
        component="admin",
        action="read",
        user_id=current_user.id,
        resource_type="users",
        resource_id="list",
        details={"params": params.model_dump(), "filters": {"role": params.role, "query": params.query}},
        ip_address=await logging_service.get_request_ip(request)
    )

    # 構建查詢條件
    conditions = []

    # 角色過濾 - 修改此部分以支援所有用戶
    if params.role:
        # 子查詢獲取特定角色的用戶ID
        role_subquery = (
            select(UserRole.user_id)
            .where(UserRole.role == params.role)
            .distinct()
            .scalar_subquery()
        )
        conditions.append(User.id.in_(role_subquery))
    # 移除此處的預設過濾，允許顯示所有使用者

    # 搜尋關鍵字
    if params.query:
        conditions.append(
            User.username.ilike(f"%{params.query}%") | User.id.ilike(f"%{params.query}%")
        )

    # 計算總數
    count_query = select(func.count(User.id))
    if conditions:
        from sqlalchemy import and_
        count_query = count_query.where(and_(*conditions))

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 建立排序
    if params.sortBy == "username":
        if params.sortOrder == "asc":
            order_by = User.username.asc()
        else:
            order_by = User.username.desc()
    else:  # default sort by createdAt
        if params.sortOrder == "asc":
            order_by = User.created_at.asc()
        else:
            order_by = User.created_at.desc()

    # 獲取用戶列表
    query = select(User).order_by(order_by)
    if conditions:
        from sqlalchemy import and_
        query = query.where(and_(*conditions))

    # 分頁
    query = query.offset((params.page - 1) * params.limit).limit(params.limit)
    result = await db.execute(query)
    users = result.scalars().all()

    # 構建回應數據
    user_list = []
    for user in users:
        # 獲取用戶角色
        roles = await get_user_roles(db, user.id)
        user_list.append({
            "userId": user.id,
            "username": user.username,
            "roles": roles,
            "createdAt": user.created_at,
        })

    return {
        "success": True,
        "data": {
            "total": total,
            "page": params.page,
            "limit": params.limit,
            "users": user_list,
        }
    }

@router.post("/{user_id}/roles", response_model=UserRoleResponse)
async def manage_user_roles(
    request: Request,
    role_action: UserRoleManage,
    user_id: str = Path(..., description="使用者ID"),
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    授權或撤銷使用者角色
    """
    # 檢查用戶是否存在
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()

    if not user:
        await logging_service.warning(
            db,
            component="admin",
            message=f"嘗試授權/撤銷角色失敗：使用者 {user_id} 不存在",
            details={"action": role_action.action, "role": role_action.role, "userId": user_id},
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "使用者不存在"
                }
            }
        )

    # 獲取用戶現有角色
    user_roles = await get_user_roles(db, user.id)

    # 授權角色
    if role_action.action == "grant":
        if role_action.role in user_roles:
            await logging_service.warning(
                db,
                component="admin",
                message=f"嘗試授權角色失敗：使用者 {user.username} 已擁有 {role_action.role} 角色",
                details={"action": "grant", "role": role_action.role, "userId": user_id},
                user_id=current_user.id,
                ip_address=await logging_service.get_request_ip(request)
            )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "error": {
                        "code": "ROLE_ALREADY_ASSIGNED",
                        "message": "使用者已擁有該角色"
                    }
                }
            )

        # 新增角色
        new_role = UserRole(
            user_id=user.id,
            role=role_action.role,
            assigned_by=current_user.id,
        )
        db.add(new_role)
        
        # 記錄角色授權
        await logging_service.audit(
            db,
            component="admin",
            action="grant_role",
            user_id=current_user.id,
            resource_type="user_role",
            resource_id=f"{user.id}/{role_action.role}",
            details={
                "targetUserId": user.id,
                "targetUsername": user.username,
                "role": role_action.role
            },
            ip_address=await logging_service.get_request_ip(request)
        )
        
        await db.commit()

        # 更新角色列表
        user_roles.append(role_action.role)

    # 撤銷角色
    elif role_action.action == "revoke":
        if role_action.role not in user_roles:
            await logging_service.warning(
                db,
                component="admin",
                message=f"嘗試撤銷角色失敗：使用者 {user.username} 未擁有 {role_action.role} 角色",
                details={"action": "revoke", "role": role_action.role, "userId": user_id},
                user_id=current_user.id,
                ip_address=await logging_service.get_request_ip(request)
            )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "error": {
                        "code": "ROLE_NOT_ASSIGNED",
                        "message": "使用者未擁有該角色，無法撤銷"
                    }
                }
            )

        # 刪除角色
        role_query = select(UserRole).where(
            (UserRole.user_id == user.id) & (UserRole.role == role_action.role)
        )
        role_result = await db.execute(role_query)
        role_obj = role_result.scalars().first()

        await db.delete(role_obj)
        
        # 記錄角色撤銷
        await logging_service.audit(
            db,
            component="admin",
            action="revoke_role",
            user_id=current_user.id,
            resource_type="user_role",
            resource_id=f"{user.id}/{role_action.role}",
            details={
                "targetUserId": user.id,
                "targetUsername": user.username,
                "role": role_action.role
            },
            ip_address=await logging_service.get_request_ip(request)
        )
        
        await db.commit()

        # 更新角色列表
        user_roles.remove(role_action.role)

    return {
        "success": True,
        "data": {
            "userId": user.id,
            "username": user.username,
            "roles": user_roles,
        }
    }