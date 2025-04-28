from datetime import date, datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator

from app.schemas import ResponseBase


# 請求物品基礎模型
class RequestItemBase(BaseModel):
    equipmentId: str = Field(..., description="器材ID")
    quantity: int = Field(..., gt=0, description="申請數量")


# 申請基礎模型
class RequestBase(BaseModel):
    startDate: date = Field(..., description="開始日期")
    endDate: date = Field(..., description="結束日期")
    venue: str = Field(..., min_length=1, max_length=100, description="使用場地/地點")
    purpose: str = Field(..., min_length=1, description="使用用途說明")
    items: List[RequestItemBase] = Field(..., min_length=1, description="借用器材清單")

    @field_validator("endDate")
    def end_date_must_be_after_start_date(cls, v, values):
        if "startDate" in values.data and v < values.data["startDate"]:
            raise ValueError("結束日期必須在開始日期之後或相同")
        return v


# 請求模型
class RequestCreate(RequestBase):
    pass


class RequestReject(BaseModel):
    reason: str = Field(..., min_length=1, description="駁回原因")


# 回應模型
class RequestCreateResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "requestId": "req_123456",
            "status": "pending_review",
            "createdAt": "2025-04-27T10:30:45Z",
        },
    )


class RequestListItem(BaseModel):
    requestId: str = Field(..., description="申請ID")
    userId: str = Field(..., description="申請人ID")
    username: str = Field(..., description="申請人名稱")
    startDate: date = Field(..., description="開始日期")
    endDate: date = Field(..., description="結束日期")
    venue: str = Field(..., description="使用場地/地點")
    status: str = Field(..., description="申請狀態")
    createdAt: datetime = Field(..., description="建立時間")

class RequestListResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "total": 45,
            "page": 1,
            "limit": 20,
            "statusCounts": {
                "pending_review": 10,
                "pending_building_response": 8,
                "pending_allocation": 5,
                "completed": 15,
                "rejected": 4,
                "closed": 3,
                "all": 45
            },
            "requests": [
                {
                    "requestId": "req_123456",
                    "userId": "user123",
                    "username": "Zhang San",
                    "startDate": "2025-05-01",
                    "endDate": "2025-05-03",
                    "venue": "中正堂",
                    "status": "pending_review",
                    "createdAt": "2025-04-27T10:30:45Z",
                }
            ],
        },
    )

class StatusHistory(BaseModel):
    status: str = Field(..., description="狀態")
    timestamp: datetime = Field(..., description="時間戳")
    operatorId: str = Field(..., description="操作者ID")
    operatorName: str = Field(..., description="操作者名稱")
    notes: Optional[str] = Field(None, description="備註")


class RequestItemDetail(BaseModel):
    itemId: str = Field(..., description="項目ID")
    equipmentName: str = Field(..., description="器材名稱")
    requestedQuantity: int = Field(..., description="申請數量")
    approvedQuantity: Optional[int] = Field(None, description="核准數量")
    allocations: List[Dict[str, Any]] = Field([], description="分配詳情")

# Token information model
class ResponseToken(BaseModel):
    tokenId: str = Field(..., description="令牌ID")
    token: str = Field(..., description="令牌值")
    createdAt: datetime = Field(..., description="創建時間")
    expiresAt: datetime = Field(..., description="過期時間")
    isUsed: bool = Field(..., description="是否已使用")

class RequestDetail(BaseModel):
    requestId: str = Field(..., description="申請ID")
    userId: str = Field(..., description="申請人ID")
    username: str = Field(..., description="申請人名稱")
    startDate: date = Field(..., description="開始日期")
    endDate: date = Field(..., description="結束日期")
    venue: str = Field(..., description="使用場地/地點")
    purpose: str = Field(..., description="使用用途說明")
    status: str = Field(..., description="申請狀態")
    createdAt: datetime = Field(..., description="建立時間")
    items: List[RequestItemDetail] = Field(..., description="借用項目")
    statusHistory: List[StatusHistory] = Field(..., description="狀態歷史")
    responseTokens: Optional[List[ResponseToken]] = Field(None, description="回覆令牌")


class RequestDetailResponse(ResponseBase):
    data: RequestDetail


class RequestCloseResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={"requestId": "req_123456", "status": "closed"},
    )


class RequestRejectResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={"requestId": "req_123456", "status": "rejected"},
    )


class RequestApproveInquiryResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "requestId": "req_123456",
            "status": "pending_building_response",
            "lineNotificationSent": True,
        },
    )