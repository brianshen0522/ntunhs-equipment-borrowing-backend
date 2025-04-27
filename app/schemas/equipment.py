from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas import ResponseBase


# 器材基礎模型
class EquipmentBase(BaseModel):
    equipmentName: str = Field(..., description="器材名稱")
    description: Optional[str] = Field(None, description="器材描述")
    enabled: Optional[bool] = Field(True, description="是否啟用")


# 請求模型
class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(EquipmentBase):
    pass


class EquipmentToggleStatus(BaseModel):
    enabled: bool = Field(..., description="啟用/停用狀態")


# 回應模型
class Equipment(EquipmentBase):
    equipmentId: str = Field(..., description="器材ID")
    createdAt: datetime = Field(..., description="建立時間")
    updatedAt: Optional[datetime] = Field(None, description="更新時間")


class EquipmentResponse(ResponseBase):
    data: Equipment


class EquipmentListItem(Equipment):
    pass


class EquipmentList(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "equipments": [
                {
                    "equipmentId": "eq_001",
                    "equipmentName": "摺疊桌",
                    "description": "標準 180cm x 75cm 會議桌",
                    "enabled": True,
                    "createdAt": "2025-01-15T08:30:00Z",
                    "updatedAt": "2025-04-20T14:30:00Z"
                }
            ]
        },
    )


class EquipmentToggleStatusResponse(ResponseBase):
    data: Equipment


class EquipmentDeleteResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={"equipmentId": "eq_003", "deleted": True},
    )