from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator

from app.schemas import ResponseBase


# 回覆項目基礎模型
class ResponseItemBase(BaseModel):
    itemId: str = Field(..., description="申請項目ID")
    availableQuantity: int = Field(..., ge=0, description="可提供數量")


# 大樓管理員回覆基礎模型
class BuildingResponseBase(BaseModel):
    buildingId: str = Field(..., description="大樓ID")
    items: List[ResponseItemBase] = Field(..., description="回覆項目")


# Building response data model for display
class BuildingResponseData(BaseModel):
    buildingId: str = Field(..., description="大樓ID")
    buildingName: str = Field(..., description="大樓名稱")
    items: List[Dict[str, Any]] = Field(..., description="回覆項目")
    submittedAt: Optional[datetime] = Field(None, description="提交時間")


# 請求模型
class BuildingResponseCreate(BuildingResponseBase):
    pass


# 回應模型
class BuildingResponseFormData(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "requestId": "req_123456",
            "requestDetails": {
                "startDate": "2025-05-01",
                "endDate": "2025-05-03",
                "venue": "中正堂",
            },
            "items": [
                {
                    "itemId": "item_001",
                    "equipmentName": "摺疊桌",
                    "requestedQuantity": 10,
                }
            ],
            "buildings": [
                {
                    "buildingId": "bldg_001",
                    "buildingName": "行政大樓",
                }
            ],
            "responseData": {
                "buildingId": "bldg_001",
                "items": [],
            },
            "allBuildingResponses": [
                {
                    "buildingId": "bldg_001",
                    "buildingName": "行政大樓",
                    "items": [
                        {
                            "itemId": "item_001",
                            "equipmentName": "摺疊桌",
                            "availableQuantity": 5,
                        }
                    ],
                    "submittedAt": "2025-04-27T14:20:30Z",
                },
                {
                    "buildingId": "bldg_002",
                    "buildingName": "護理學院大樓",
                    "items": [
                        {
                            "itemId": "item_001",
                            "equipmentName": "摺疊桌",
                            "availableQuantity": 3,
                        }
                    ],
                    "submittedAt": "2025-04-27T16:45:20Z",
                }
            ],
        },
    )


class BuildingResponseCreateResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "responseId": "resp_123456",
            "requestId": "req_123456",
            "buildingId": "bldg_001",
            "buildingName": "行政大樓",
            "submittedAt": "2025-04-27T14:20:30Z",
        },
    )


class BuildingResponseItem(BaseModel):
    itemId: str = Field(..., description="項目ID")
    equipmentName: str = Field(..., description="器材名稱")
    availableQuantity: int = Field(..., description="可提供數量")


class BuildingResponseDetail(BaseModel):
    responseId: str = Field(..., description="回覆ID")
    buildingId: str = Field(..., description="大樓ID")
    buildingName: str = Field(..., description="大樓名稱")
    submittedAt: datetime = Field(..., description="提交時間")
    items: List[BuildingResponseItem] = Field(..., description="回覆項目")


class TotalAvailableItem(BaseModel):
    itemId: str = Field(..., description="項目ID")
    equipmentName: str = Field(..., description="器材名稱")
    requestedQuantity: int = Field(..., description="申請數量")
    totalAvailableQuantity: int = Field(..., description="總可用數量")


class BuildingResponseListResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "responses": [
                {
                    "responseId": "resp_123456",
                    "buildingId": "bldg_001",
                    "buildingName": "行政大樓",
                    "submittedAt": "2025-04-27T14:20:30Z",
                    "items": [
                        {
                            "itemId": "item_001",
                            "equipmentName": "摺疊桌",
                            "availableQuantity": 8,
                        }
                    ],
                }
            ],
            "totalAvailable": [
                {
                    "itemId": "item_001",
                    "equipmentName": "摺疊桌",
                    "requestedQuantity": 10,
                    "totalAvailableQuantity": 8,
                }
            ],
        },
    )