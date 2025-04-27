from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.users import User, UserRole
from app.models.settings import SystemLog

# 使用HTTP Bearer Token身分驗證
security = HTTPBearer()

class TokenPayload:
    """
    JWT 令牌的載荷格式
    """

    def __init__(self, sub: str, role: str, exp: int):
        self.sub = sub
        self.role = role
        self.exp = exp


async def create_access_token(user_id: str, role: str) -> str:
    """
    創建 JWT 訪問令牌
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": user_id, "role": role, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def verify_ntunhs_credentials(username: str, password: str, db: AsyncSession) -> Dict[str, Any]:
    """
    驗證學校登入系統認證
    
    使用學校登入API進行驗證，API僅返回true或false
    """
    try:
        # 嘗試記錄驗證嘗試
        log = SystemLog(
            level="info",
            component="auth",
            message=f"嘗試驗證用戶 {username}",
            details=None
        )
        db.add(log)
        await db.commit()
        
        # 實際應用中，這裡會調用學校的API
        login_url = settings.SSO_URL
        
        async with httpx.AsyncClient() as client:
            params = {
                "txtid": username,
                "txtpwd": password
            }
            response = await client.post(login_url, params=params, timeout=10.0)
            
            # 假設API返回的是純文本 "true" 或 "false"
            is_valid = response.text.strip().lower() == "true"
            
            if is_valid:
                # 簡化處理：在實際應用中，這裡可能需要更複雜的邏輯來獲取用戶信息
                # 由於API僅返回true/false，這裡使用用戶輸入的ID作為用戶資訊
                return {
                    "id": username,  # 使用學號作為ID
                    "username": username,  # 使用學號作為顯示名稱，實際中可能需要從另一個API獲取
                    "email": f"{username}@example.com",  # 模擬郵箱
                    "roles": ["applicant"]  # 默認角色為申請人
                }
            return None
    except Exception as e:
        # 記錄錯誤
        error_log = SystemLog(
            level="error",
            component="auth",
            message=f"驗證用戶失敗: {str(e)}",
            details=None
        )
        db.add(error_log)
        await db.commit()
        
        # 開發環境中使用模擬帳號
        if settings.APP_ENV == "development":
            # 模擬的驗證結果
            if username == "admin" and password == "admin":
                return {
                    "id": "admin001",
                    "username": "管理員",
                    "email": "admin@ntunhs.edu.tw",
                    "roles": ["applicant", "academic_staff", "system_admin"],
                }
            elif username == "staff" and password == "staff":
                return {
                    "id": "staff001",
                    "username": "教務處人員",
                    "email": "staff@ntunhs.edu.tw",
                    "roles": ["applicant", "academic_staff"],
                }
            elif username == "user" and password == "user":
                return {
                    "id": "user001",
                    "username": "一般使用者",
                    "email": "user@ntunhs.edu.tw",
                    "roles": ["applicant"],
                }
        return None


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    根據 ID 獲取使用者
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_user_roles(db: AsyncSession, user_id: str) -> List[str]:
    """
    獲取使用者的所有角色
    """
    query = select(UserRole.role).where(UserRole.user_id == user_id)
    result = await db.execute(query)
    roles = result.scalars().all()
    return roles


async def create_user_if_not_exists(
    db: AsyncSession, user_id: str, username: str, email: str, roles: List[str]
) -> User:
    """
    如果使用者不存在，則建立使用者記錄
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        user = User(id=user_id, username=username, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # 新增角色
        for role in roles:
            db.add(UserRole(user_id=user_id, role=role))
        await db.commit()
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    獲取當前登入的使用者
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無效的認證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None or role is None:
            raise credentials_exception
        token_payload = TokenPayload(sub=user_id, role=role, exp=payload.get("exp"))
    except (JWTError, ValidationError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    # 更新最後登入時間
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    獲取當前活躍的使用者
    """
    return current_user


async def get_current_user_with_role(
    required_role: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> User:
    """
    驗證當前使用者是否擁有指定角色
    """
    user_roles = await get_user_roles(db, current_user.id)
    if required_role not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="權限不足，需要 {} 角色".format(required_role)
        )
    return current_user