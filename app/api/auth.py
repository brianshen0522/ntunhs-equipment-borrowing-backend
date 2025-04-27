from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    使用學校認證系統登入
    """
    # 驗證學校系統憑證
    sso_user = await verify_ntunhs_credentials(login_data.username, login_data.password, db)
    if not sso_user:
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
    
    return LoginResponse(data={"token": token, "role": role})


@router.post("/logout", response_model=SimpleResponse)
async def logout(current_user: User = Depends(get_current_user)) -> Any:
    """
    登出系統
    
    註： JWT 令牌無法在服務端撤銷，客戶端需自行移除令牌
    """
    return SimpleResponse(success=True)


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取當前登入使用者的資訊
    """
    # 獲取使用者所有角色
    all_roles = await get_user_roles(db, current_user.id)
    
    return UserInfoResponse(
        data={
            "userId": current_user.id,
            "username": current_user.username,
            "role": "applicant",  # 根據實際認證中的角色獲取
            "allRoles": all_roles,
        }
    )