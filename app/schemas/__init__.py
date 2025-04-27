from datetime import date, datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field


# 通用回應模型
class ResponseBase(BaseModel):
    success: bool = True


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    issue: Optional[str] = None


class ErrorResponse(ResponseBase):
    success: bool = False
    error: Dict[str, Any] = Field(
        ...,
        example={
            "code": "ERROR_CODE",
            "message": "錯誤描述訊息",
            "details": {"field": "有問題的欄位", "issue": "具體問題說明"},
        },
    )


# 通用分頁參數
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


# 通用排序參數
class SortParams(BaseModel):
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "desc"  # asc or desc