from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_academic_staff_user
from app.database import get_db
from app.models.users import User
from app.crud.allocations import allocation as crud_allocation
from app.crud.requests import request as crud_request
from app.schemas.allocations import (
    AllocationCreate,
    AllocationResponse,
    ResendEmailResponse,
)

router = APIRouter(prefix="/requests", tags=["allocations"])


@router.post("/{request_id}/allocate", response_model=AllocationResponse)
async def allocate_equipment(
    allocation_in: AllocationCreate,
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    教務處人員進行器材分配
    """
    # 檢查申請是否存在
    request_detail = await crud_request.get_request_detail(db, request_id=request_id)
    if not request_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "申請不存在"
                }
            }
        )
    
    # 檢查申請狀態是否為待分配
    if request_detail["status"] != "pending_allocation":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_STATE",
                    "message": "只能對待分配狀態的申請進行分配",
                    "details": {
                        "currentStatus": request_detail["status"]
                    }
                }
            }
        )
    
    # 分配器材
    try:
        request = await crud_allocation.allocate_equipment(
            db, request_id=request_id, obj_in=allocation_in, operator_id=current_user.id
        )
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "申請不存在"
                    }
                }
            )
        
        # 生成 PDF
        pdf_path = await crud_allocation.generate_pdf(db, request_id=request_id)
        
        # 發送郵件
        email_sent = False
        if pdf_path:
            recipient_email = await crud_allocation.send_email(db, request_id=request_id)
            email_sent = recipient_email is not None
        
        # 如果 PDF 生成失敗
        if not pdf_path:
            return {
                "success": True,
                "data": {
                    "requestId": request.id,
                    "status": request.status,
                    "pdfUrl": None,
                    "warning": "PDF生成失敗，請稍後重試"
                }
            }
        
        return {
            "success": True,
            "data": {
                "requestId": request.id,
                "status": request.status,
                "pdfUrl": f"/api/requests/{request_id}/pdf"
            }
        }
        
    except ValueError as e:
        # 數量驗證錯誤
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "分配數量驗證失敗",
                    "details": [
                        {
                            "field": "allocations[0].buildingAllocations",
                            "issue": str(e)
                        }
                    ]
                }
            }
        )


@router.post("/{request_id}/resend-email", response_model=ResendEmailResponse)
async def resend_email(
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    重新發送借用單郵件給申請人
    """
    # 檢查申請是否存在
    request_detail = await crud_request.get_request_detail(db, request_id=request_id)
    if not request_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "申請不存在"
                }
            }
        )
    
    # 檢查申請狀態是否為已完成
    if request_detail["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "申請不存在或尚未完成分配"
                }
            }
        )
    
    # 發送郵件
    recipient_email = await crud_allocation.send_email(db, request_id=request_id)
    
    if not recipient_email:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "EMAIL_SENDING_FAILED",
                    "message": "郵件發送失敗，請稍後重試"
                }
            }
        )
    
    return {
        "success": True,
        "data": {
            "requestId": request_id,
            "emailSent": True,
            "sentTo": recipient_email
        }
    }