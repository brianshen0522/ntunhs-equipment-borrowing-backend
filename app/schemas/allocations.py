from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator

from app.schemas import ResponseBase


# 建築分配基礎模型
class BuildingAllocationBase(BaseModel):
    buildingId: str = Field(..., description="大樓ID")
    allocatedQuantity: int = Field(..., gt=0, description="分配數量")


# 項目分配基礎模型
class ItemAllocationBase(BaseModel):
    itemId: str = Field(..., description="項目ID")
    approvedQuantity: int = Field(..., gt=0, description="核准數量")
    buildingAllocations: List[BuildingAllocationBase] = Field(..., min_length=1, description="大樓分配")

    @field_validator("buildingAllocations")
    def validate_total_allocation(cls, v, values):
        if "approvedQuantity" in values.data:
            total_allocated = sum(item.allocatedQuantity for item in v)
            if total_allocated != values.data["approvedQuantity"]:
                raise ValueError(f"分配總數 {total_allocated} 必須等於核准數量 {values.data['approvedQuantity']}")
        return v


# 請求模型
class AllocationCreate(BaseModel):
    allocations: List[ItemAllocationBase] = Field(..., min_length=1, description="項目分配")
    notes: Optional[str] = Field(None, description="備註")


# 回應模型
class AllocationResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "requestId": "req_123456",
            "status": "completed",
            "pdfUrl": "/api/requests/req_123456/pdf",
        },
    )


class ResendEmailResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "requestId": "req_123456",
            "emailSent": True,
            "sentTo": "applicant@example.com",
        },
    )