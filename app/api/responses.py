from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.crud.responses import response as crud_response
from app.schemas.responses import (
    BuildingResponseCreate,
    BuildingResponseFormData,
    BuildingResponseCreateResponse,
)

router = APIRouter(tags=["building_responses"])


@router.get("/building-response/{response_token}", response_model=BuildingResponseFormData)
async def get_form_data(
    response_token: str = Path(..., description="專屬回覆令牌"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    大樓管理員通過專屬連結獲取填表頁面數據
    """
    # 檢查令牌是否有效
    token_obj = await crud_response.get_token_by_token(db, token=response_token)
    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "回覆令牌無效"
                }
            }
        )

    # 獲取表單數據
    form_data = await crud_response.get_form_data(db, token=response_token)
    if not form_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "對應的申請不存在或已結束"
                }
            }
        )

    return {
        "success": True,
        "data": form_data,
    }


@router.post("/building-response/{response_token}", response_model=BuildingResponseCreateResponse)
async def submit_response(
    response_in: BuildingResponseCreate,
    response_token: str = Path(..., description="專屬回覆令牌"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    大樓管理員提交可提供的器材數量
    """
    # 獲取客戶端 IP
    client_ip = request.client.host if request else None

    # 檢查令牌是否有效
    token_obj = await crud_response.get_token_by_token(db, token=response_token)
    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "回覆令牌無效"
                }
            }
        )

    # 檢查令牌是否過期
    from datetime import datetime
    if token_obj.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "success": False,
                "error": {
                    "code": "EXPIRED",
                    "message": "填表連結已過期"
                }
            }
        )

    # 檢查令牌是否已標記為完成（分配已完成）
    if token_obj.is_finished:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "success": False,
                "error": {
                    "code": "FORM_COMPLETED",
                    "message": "此表單已完成分配，無法再次提交"
                }
            }
        )

    # 提交回覆
    response = await crud_response.submit_response(
        db, token=response_token, obj_in=response_in, ip_address=client_ip
    )

    if not response:
        # 檢查是否是參數無效
        form_data = await crud_response.get_form_data(db, token=response_token)
        if not form_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "大樓或器材項目不存在"
                    }
                }
            )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "數量驗證失敗",
                    "details": [
                        {
                            "field": "items[0].equipmentId",
                            "issue": "數量必須為正整數"
                        }
                    ]
                }
            }
        )

    # 獲取大樓名稱
    from sqlalchemy import select
    from app.models.buildings import Building
    building_query = select(Building).where(Building.id == response.building_id)
    building_result = await db.execute(building_query)
    building = building_result.scalars().first()
    building_name = building.name if building else "未知大樓"

    return {
        "success": True,
        "data": {
            "responseId": response.id,
            "requestId": response.request_id,
            "buildingId": response.building_id,
            "buildingName": building_name,
            "submittedAt": response.submitted_at,
        }
    }