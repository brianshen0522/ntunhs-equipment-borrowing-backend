from datetime import date
from typing import Any, List, Optional
import os
from pathlib import Path as FilePath

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_applicant_user, get_academic_staff_user
from app.database import get_db
from app.models.users import User
from app.crud.requests import request as crud_request
from app.crud.responses import response as crud_response
from app.crud.allocations import allocation as crud_allocation
from app.schemas.requests import (
    RequestCreate,
    RequestCreateResponse,
    RequestListResponse,
    RequestDetailResponse,
    RequestCloseResponse,
    RequestReject,
    RequestRejectResponse,
    RequestApproveInquiryResponse,
)
from app.schemas.responses import BuildingResponseListResponse

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=RequestCreateResponse)
async def create_request(
    request_in: RequestCreate,
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    創建新的器材借用申請
    """
    # 創建申請
    db_request = await crud_request.create_with_items(db, obj_in=request_in, user_id=current_user.id)
    
    return {
        "success": True,
        "data": {
            "requestId": db_request.id,
            "status": db_request.status,
            "createdAt": db_request.created_at,
        }
    }


@router.get("", response_model=RequestListResponse)
async def get_requests(
    page: int = Query(1, ge=1, description="頁碼"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
    status: Optional[str] = Query(None, description="過濾狀態"),
    startDateFrom: Optional[date] = Query(None, description="開始日期下限"),
    startDateTo: Optional[date] = Query(None, description="開始日期上限"),
    userId: Optional[str] = Query(None, description="申請人ID (僅教務處人員可用)"),
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取借用申請列表
    """
    # 判斷是否為教務處人員
    is_academic_staff = False
    try:
        current_user = await get_academic_staff_user(db, current_user)
        is_academic_staff = True
    except:
        pass
    
    # 非教務處人員只能查看自己的申請
    if not is_academic_staff and userId and userId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "FORBIDDEN",
                    "message": "無權查看其他使用者的申請"
                }
            }
        )
    
    # 獲取申請列表
    requests, total = await crud_request.get_requests(
        db,
        user_id=userId if is_academic_staff else current_user.id,
        status=status,
        start_date_from=startDateFrom,
        start_date_to=startDateTo,
        skip=(page - 1) * limit,
        limit=limit,
        is_admin=is_academic_staff,
    )
    
    return {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "limit": limit,
            "requests": requests,
        }
    }


@router.get("/{request_id}", response_model=RequestDetailResponse)
async def get_request_detail(
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取特定借用申請的詳情
    """
    # 獲取申請詳情
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

    # 判斷是否為教務處人員
    is_academic_staff = False
    try:
        current_user = await get_academic_staff_user(db, current_user)
        is_academic_staff = True
    except:
        pass

    # 非教務處人員只能查看自己的申請
    if not is_academic_staff and request_detail["userId"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "FORBIDDEN",
                    "message": "無權查看該申請"
                }
            }
        )

    return {
        "success": True,
        "data": request_detail,
    }

@router.post("/{request_id}/close", response_model=RequestCloseResponse)
async def close_request(
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    申請人關閉尚未處理的申請
    """
    # 關閉申請
    request = await crud_request.close_request(db, request_id=request_id, user_id=current_user.id)
    
    if not request:
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
        
        # 檢查是否為申請人
        if request_detail["userId"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "只有申請人可以關閉申請"
                    }
                }
            )
        
        # 檢查狀態
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_STATE",
                    "message": "只能關閉待審核狀態的申請",
                    "details": {
                        "currentStatus": request_detail["status"]
                    }
                }
            }
        )
    
    return {
        "success": True,
        "data": {
            "requestId": request.id,
            "status": request.status,
        }
    }


@router.post("/{request_id}/reject", response_model=RequestRejectResponse)
async def reject_request(
    request_in: RequestReject,
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    教務處人員駁回申請
    """
    # 駁回申請
    request = await crud_request.reject_request(
        db, request_id=request_id, operator_id=current_user.id, reason=request_in.reason
    )
    
    if not request:
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
        
        # 檢查狀態
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_STATE",
                    "message": "只能駁回待審核狀態的申請",
                    "details": {
                        "currentStatus": request_detail["status"]
                    }
                }
            }
        )
    
    return {
        "success": True,
        "data": {
            "requestId": request.id,
            "status": request.status,
        }
    }


@router.post("/{request_id}/approve-inquiry", response_model=RequestApproveInquiryResponse)
async def approve_inquiry(
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    教務處人員同意詢問大樓管理員
    """
    # 同意詢問
    request = await crud_request.approve_inquiry(db, request_id=request_id, operator_id=current_user.id)
    
    if not request:
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
        
        # 檢查狀態
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_STATE",
                    "message": "只能同意待審核狀態的申請",
                    "details": {
                        "currentStatus": request_detail["status"]
                    }
                }
            }
        )
    
    # 創建回覆令牌
    token = await crud_response.create_token(db, request_id=request_id)
    
    # 實際應用中這裡會發送 LINE 通知
    line_notification_sent = True
    
    return {
        "success": True,
        "data": {
            "requestId": request.id,
            "status": request.status,
            "lineNotificationSent": line_notification_sent,
        }
    }


@router.get("/{request_id}/building-responses", response_model=BuildingResponseListResponse)
async def get_building_responses(
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    教務處人員獲取特定申請的大樓管理員回覆列表
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
    
    # 獲取回覆列表
    responses, total_available = await crud_response.get_responses(db, request_id=request_id)
    
    return {
        "success": True,
        "data": {
            "responses": responses,
            "totalAvailable": total_available,
        }
    }


@router.get("/{request_id}/pdf")
async def get_request_pdf(
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_applicant_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    生成器材借用單 PDF
    """
    # 獲取申請詳情
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
    
    # 判斷是否為教務處人員
    is_academic_staff = False
    try:
        current_user = await get_academic_staff_user(db, current_user)
        is_academic_staff = True
    except:
        pass
    
    # 非教務處人員只能查看自己的申請
    if not is_academic_staff and request_detail["userId"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "FORBIDDEN",
                    "message": "無權查看該申請的PDF"
                }
            }
        )
    
    # 檢查申請狀態
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
    
    # 獲取PDF路徑 - 從申請記錄中獲取或生成新的
    pdf_path = None
    # 如果有現有PDF路徑
    if "pdf_path" in request_detail and request_detail["pdf_path"]:
        pdf_path = request_detail["pdf_path"]
    else:
        # 生成 PDF
        pdf_path = await crud_allocation.generate_pdf(db, request_id=request_id)
    
    if not pdf_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "PDF_GENERATION_FAILED",
                    "message": "PDF生成失敗，請稍後重試"
                }
            }
        )
    
    # 構建完整的檔案路徑
    # 如果pdf_path是相對路徑，將其轉換為絕對路徑
    if pdf_path.startswith('/'):
        pdf_path = pdf_path[1:]  # 移除開頭的'/'
    
    full_path = FilePath(os.getcwd()) / pdf_path
    
    # 檢查檔案是否存在
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": "PDF檔案不存在，請重新生成"
                }
            }
        )
    
    # 返回PDF檔案
    return FileResponse(
        path=full_path,
        filename=f"器材借用單_{request_id}.pdf",
        media_type="application/pdf"
    )


@router.post("/{request_id}/resend-email")
async def resend_email(
    request_id: str = Path(..., description="申請ID"),
    current_user: User = Depends(get_academic_staff_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    重新發送借用單郵件給申請人
    """
    # 獲取申請詳情
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
    
    # 檢查申請狀態
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
    email = await crud_allocation.send_email(db, request_id=request_id)
    
    if not email:
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
            "sentTo": email,
        }
    }