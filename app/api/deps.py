from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, get_current_user_with_role
from app.database import get_db
from app.models.users import User


# 依賴函數：獲取已認證的使用者
async def get_applicant_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """
    依賴函數：獲取具有申請人角色的認證使用者
    """
    return await get_current_user_with_role("applicant", current_user, db)


async def get_academic_staff_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """
    依賴函數：獲取具有教務處人員角色的認證使用者
    """
    return await get_current_user_with_role("academic_staff", current_user, db)


async def get_system_admin_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """
    依賴函數：獲取具有系統管理員角色的認證使用者
    """
    return await get_current_user_with_role("system_admin", current_user, db)