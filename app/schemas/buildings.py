from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas import ResponseBase


# 大樓基礎模型
class BuildingBase(BaseModel):
    buildingName: str = Field(..., description="大樓名稱")


# 請求模型
class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BuildingBase):
    pass


class BuildingToggleStatus(BaseModel):
    enabled: bool = Field(..., description="啟用/停用狀態")


# 回應模型
class Building(BuildingBase):
    buildingId: str = Field(..., description="大樓ID")
    buildingName: str = Field(..., description="大樓名稱")
    enabled: bool = Field(..., description="啟用/停用狀態")
    createdAt: datetime = Field(..., description="建立時間")


class BuildingResponse(ResponseBase):
    data: Building


class BuildingListItem(Building):
    pass


class BuildingList(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "buildings": [
                {
                    "buildingId": "bldg_001",
                    "buildingName": "行政大樓",
                    "enabled": True,
                    "createdAt": "2025-01-15T08:30:00Z",
                }
            ]
        },
    )


class BuildingToggleStatusResponse(ResponseBase):
    data: Building


class BuildingDeleteResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={"buildingId": "bldg_003", "deleted": True},
    )