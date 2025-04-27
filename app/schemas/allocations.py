from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas import ResponseBase


# 建築分配基礎模型
class BuildingAllocationBase(BaseModel):
    buildingId: str = Field(..., description="大樓ID")
    allocatedQuantity: int = Field(..., gt=0, description="分配數量")


# 項目分配基礎模型
class ItemAllocationBase(BaseModel):
    itemId: str = Field(..., description="項目ID")
    approvedQuantity: int = Field(..., ge=0, description="核准數量")  # Changed from gt=0 to ge=0
    buildingAllocations: List[BuildingAllocationBase] = Field([], description="大樓分配")

    @model_validator(mode='after')
    def validate_allocation_consistency(self) -> 'ItemAllocationBase':
        # 如果核准數量為0，允許空的分配列表
        if self.approvedQuantity == 0:
            if self.buildingAllocations:
                raise ValueError("當核准數量為0時，分配列表必須為空")
            return self
            
        # 如果核准數量大於0，檢查分配列表不能為空
        if not self.buildingAllocations:
            raise ValueError("當核准數量大於0時，必須至少有一個分配")
            
        # 檢查分配總數是否等於核准數量
        total_allocated = sum(item.allocatedQuantity for item in self.buildingAllocations)
        if total_allocated != self.approvedQuantity:
            raise ValueError(f"分配總數 {total_allocated} 必須等於核准數量 {self.approvedQuantity}")
            
        return self


# 請求模型
class AllocationCreate(BaseModel):
    allocations: List[ItemAllocationBase] = Field(..., description="項目分配")
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