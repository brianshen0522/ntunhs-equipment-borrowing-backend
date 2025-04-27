from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas import ResponseBase


# 請求模型
class LoginRequest(BaseModel):
    username: str = Field(..., description="使用者名稱")
    password: str = Field(..., description="使用者密碼")
    selectedRole: Optional[str] = Field(None, description="選擇的角色 (若有多個)")


# 回應模型
class TokenData(BaseModel):
    token: str = Field(..., description="JWT令牌")
    role: Optional[str] = Field(None, description="使用者角色")
    roles: Optional[List[str]] = Field(None, description="使用者所有角色清單")
    needRoleSelection: Optional[bool] = Field(None, description="是否需要選擇角色")


class LoginResponse(ResponseBase):
    data: TokenData


class UserInfo(BaseModel):
    userId: str = Field(..., description="使用者ID")
    username: str = Field(..., description="使用者名稱")
    role: str = Field(..., description="當前角色")
    allRoles: List[str] = Field(..., description="所有角色")


class UserInfoResponse(ResponseBase):
    data: UserInfo


class SimpleResponse(ResponseBase):
    """簡單成功回應"""
    pass