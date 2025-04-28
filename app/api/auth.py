from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_applicant_user
from app.core.auth import (
    create_access_token,
    create_user_if_not_exists,
    get_current_user,
    get_user_roles,
    verify_ntunhs_credentials,
)
from app.database import get_db
from app.models.users import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SimpleResponse,
    UserInfo,
    UserInfoResponse,
)
from app.services.logging import logging_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest, 
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    使用學校認證系統登入
    """
    # 記錄登入嘗試（不記錄密碼）
    await logging_service.info(
        db,
        component="auth",
        message=f"用戶 {login_data.username} 嘗試登入",
        details={"username": login_data.username},
        ip_address=await logging_service.get_request_ip(request)
    )
    
    # 驗證學校系統憑證
    sso_user = await verify_ntunhs_credentials(login_data.username, login_data.password, db)
    if not sso_user:
        # 記錄登入失敗
        await logging_service.warning(
            db,
            component="auth",
            message=f"用戶 {login_data.username} 登入失敗：帳號或密碼錯誤",
            details={"username": login_data.username, "reason": "invalid_credentials"},
            ip_address=await logging_service.get_request_ip(request)
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
        )

    # 獲取或創建使用者
    user = await create_user_if_not_exists(
        db,
        sso_user["id"],
        sso_user["username"],
        sso_user["email"],
        sso_user["roles"]
    )

    # 獲取使用者角色
    user_roles = await get_user_roles(db, user.id)

    # 如果有多個角色但未選擇，返回角色選擇
    if len(user_roles) > 1 and login_data.selectedRole is None:
        token = await create_access_token(user.id, "applicant")  # 默認使用 applicant 角色
        
        # 記錄登入成功，需要選擇角色
        await logging_service.info(
            db,
            component="auth",
            message=f"用戶 {user.username} 登入成功：需要選擇角色",
            details={
                "userId": user.id,
                "username": user.username,
                "availableRoles": user_roles
            },
            user_id=user.id,
            ip_address=await logging_service.get_request_ip(request)
        )
        
        return LoginResponse(
            data={
                "token": token,
                "roles": user_roles,
                "needRoleSelection": True,
            }
        )

    # 如果選擇了角色，驗證是否有該角色權限
    if login_data.selectedRole is not None:
        if login_data.selectedRole not in user_roles:
            # 記錄角色選擇失敗
            await logging_service.warning(
                db,
                component="auth",
                message=f"用戶 {user.username} 嘗試使用未授權的角色",
                details={
                    "userId": user.id,
                    "username": user.username,
                    "requestedRole": login_data.selectedRole,
                    "availableRoles": user_roles
                },
                user_id=user.id,
                ip_address=await logging_service.get_request_ip(request)
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="使用者沒有所選角色的權限",
            )
        role = login_data.selectedRole
    else:
        # 只有一個角色，直接使用
        role = user_roles[0]

    # 創建訪問令牌
    token = await create_access_token(user.id, role)

    # 更新最後登入時間
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # 記錄登入成功
    await logging_service.audit(
        db,
        component="auth",
        action="login",
        user_id=user.id,
        resource_type="session",
        resource_id=user.id,
        details={
            "username": user.username,
            "role": role,
            "loginTime": datetime.utcnow().isoformat()
        },
        ip_address=await logging_service.get_request_ip(request)
    )

    return LoginResponse(data={"token": token, "role": role})


@router.post("/logout", response_model=SimpleResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    登出系統

    註： JWT 令牌無法在服務端撤銷，客戶端需自行移除令牌
    """
    # 記錄登出
    await logging_service.audit(
        db,
        component="auth",
        action="logout",
        user_id=current_user.id,
        resource_type="session",
        resource_id=current_user.id,
        details={
            "username": current_user.username,
            "logoutTime": datetime.utcnow().isoformat()
        },
        ip_address=await logging_service.get_request_ip(request)
    )
    
    return SimpleResponse(success=True)


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取當前登入使用者的資訊
    """
    # 獲取使用者所有角色
    all_roles = await get_user_roles(db, current_user.id)
    
    # 記錄查詢操作
    await logging_service.info(
        db,
        component="auth",
        message=f"用戶 {current_user.username} 查詢個人資訊",
        user_id=current_user.id,
        ip_address=await logging_service.get_request_ip(request)
    )

    return UserInfoResponse(
        data={
            "userId": current_user.id,
            "username": current_user.username,
            "role": "applicant",  # 根據實際認證中的角色獲取
            "allRoles": all_roles,
        }
    )