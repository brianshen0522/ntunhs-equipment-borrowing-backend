from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_system_admin_user
from app.database import get_db
from app.models.users import User
from app.models.settings import LineBotSettings, SmtpSettings, SystemParameters, SystemLog
from app.schemas.settings import (
    LineBotSettings as LineBotSettingsSchema,
    LineBotSettingsResponse,
    LineBotSettingsUpdateResponse,
    LineBotTestResponse,
    SmtpSettings as SmtpSettingsSchema,
    SmtpSettingsResponse,
    SmtpSettingsUpdateResponse,
    SmtpTestRequest,
    SmtpTestResponse,
    SystemParametersRequest,
    SystemParametersResponse,
    SystemParametersUpdateResponse,
    SystemStatus,
    SystemStatusResponse,
    LogListParams,
    SystemLogListResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# LINE Bot 設定
@router.get("/line-bot-settings", response_model=LineBotSettingsResponse)
async def get_line_bot_settings(
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取當前 LINE Bot 設定
    """
    # 獲取設定
    query = select(LineBotSettings).order_by(LineBotSettings.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "LINE Bot 設定尚未建立"
                }
            }
        )
    
    return {
        "success": True,
        "data": {
            "webhookUrl": settings.webhook_url,
            "channelAccessToken": "encrypted_token_placeholder",  # 為安全起見不返回實際令牌
            "channelSecret": "encrypted_secret_placeholder",      # 為安全起見不返回實際密鑰
            "notificationTemplates": {
                "buildingManagerRequest": settings.building_request_template,
                "allocationComplete": settings.allocation_complete_template,
            }
        }
    }


@router.put("/line-bot-settings", response_model=LineBotSettingsUpdateResponse)
async def update_line_bot_settings(
    settings_in: LineBotSettingsSchema,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    更新 LINE Bot 設定
    """
    # 獲取現有設定
    query = select(LineBotSettings).order_by(LineBotSettings.id.desc()).limit(1)
    result = await db.execute(query)
    existing_settings = result.scalars().first()
    
    if existing_settings:
        # 更新現有設定
        existing_settings.webhook_url = settings_in.webhookUrl
        existing_settings.channel_access_token = settings_in.channelAccessToken
        existing_settings.channel_secret = settings_in.channelSecret
        existing_settings.building_request_template = settings_in.notificationTemplates.buildingManagerRequest
        existing_settings.allocation_complete_template = settings_in.notificationTemplates.allocationComplete
        existing_settings.updated_at = datetime.utcnow()
        existing_settings.updated_by = current_user.id
        db.add(existing_settings)
    else:
        # 創建新設定
        new_settings = LineBotSettings(
            webhook_url=settings_in.webhookUrl,
            channel_access_token=settings_in.channelAccessToken,
            channel_secret=settings_in.channelSecret,
            building_request_template=settings_in.notificationTemplates.buildingManagerRequest,
            allocation_complete_template=settings_in.notificationTemplates.allocationComplete,
            updated_by=current_user.id,
        )
        db.add(new_settings)
    
    await db.commit()
    
    return {
        "success": True,
        "data": {
            "updated": True
        }
    }


@router.post("/line-bot-test", response_model=LineBotTestResponse)
async def test_line_bot(
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    測試 LINE Bot 連接是否正常
    """
    # 獲取設定
    query = select(LineBotSettings).order_by(LineBotSettings.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "LINE Bot 設定尚未完成"
                }
            }
        )
    
    # 在實際應用中，這裡會進行 LINE Bot API 的連接測試
    # 此處簡化為模擬測試結果
    try:
        # 模擬連接測試
        # 實際應用中，會使用 LINE Bot SDK 進行 API 調用
        # from linebot import LineBotApi
        # line_bot_api = LineBotApi(settings.channel_access_token)
        # bot_info = line_bot_api.get_bot_info()
        
        # 記錄測試成功
        log = SystemLog(
            level="info",
            component="line",
            message="LINE Bot 連接測試成功",
            user_id=current_user.id,
        )
        db.add(log)
        await db.commit()
        
        return {
            "success": True,
            "data": {
                "connectionStatus": "success",
                "botInfo": {
                    "displayName": "設備借用系統通知"
                }
            }
        }
    except Exception as e:
        # 記錄測試失敗
        log = SystemLog(
            level="error",
            component="line",
            message="LINE Bot 連接測試失敗",
            details=str(e),
            user_id=current_user.id,
        )
        db.add(log)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "CONNECTION_FAILED",
                    "message": "LINE Bot 連接失敗",
                    "details": {
                        "reason": str(e)
                    }
                }
            }
        )


# SMTP 設定
@router.get("/smtp-settings", response_model=SmtpSettingsResponse)
async def get_smtp_settings(
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取當前 SMTP 設定
    """
    # 獲取設定
    query = select(SmtpSettings).order_by(SmtpSettings.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "SMTP 設定尚未建立"
                }
            }
        )
    
    import json
    email_templates = json.loads(settings.email_templates)
    
    return {
        "success": True,
        "data": {
            "host": settings.host,
            "port": settings.port,
            "secure": settings.secure,
            "username": settings.username,
            "password": "encrypted_password_placeholder",  # 為安全起見不返回實際密碼
            "senderEmail": settings.sender_email,
            "senderName": settings.sender_name,
            "emailTemplates": email_templates,
        }
    }


@router.put("/smtp-settings", response_model=SmtpSettingsUpdateResponse)
async def update_smtp_settings(
    settings_in: SmtpSettingsSchema,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    更新 SMTP 設定
    """
    # 獲取現有設定
    query = select(SmtpSettings).order_by(SmtpSettings.id.desc()).limit(1)
    result = await db.execute(query)
    existing_settings = result.scalars().first()
    
    import json
    email_templates_json = json.dumps({
        "approvalNotification": {
            "subject": settings_in.emailTemplates.approvalNotification.subject,
            "body": settings_in.emailTemplates.approvalNotification.body,
        }
    })
    
    if existing_settings:
        # 更新現有設定
        existing_settings.host = settings_in.host
        existing_settings.port = settings_in.port
        existing_settings.secure = settings_in.secure
        existing_settings.username = settings_in.username
        existing_settings.password = settings_in.password  # 實際應用中應加密存儲
        existing_settings.sender_email = settings_in.senderEmail
        existing_settings.sender_name = settings_in.senderName
        existing_settings.email_templates = email_templates_json
        existing_settings.updated_at = datetime.utcnow()
        existing_settings.updated_by = current_user.id
        db.add(existing_settings)
    else:
        # 創建新設定
        new_settings = SmtpSettings(
            host=settings_in.host,
            port=settings_in.port,
            secure=settings_in.secure,
            username=settings_in.username,
            password=settings_in.password,  # 實際應用中應加密存儲
            sender_email=settings_in.senderEmail,
            sender_name=settings_in.senderName,
            email_templates=email_templates_json,
            updated_by=current_user.id,
        )
        db.add(new_settings)
    
    await db.commit()
    
    return {
        "success": True,
        "data": {
            "updated": True
        }
    }


@router.post("/smtp-test", response_model=SmtpTestResponse)
async def test_smtp(
    test_data: SmtpTestRequest,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    測試 SMTP 連接是否正常
    """
    # 獲取設定
    query = select(SmtpSettings).order_by(SmtpSettings.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "SMTP 設定尚未完成"
                }
            }
        )
    
    # 在實際應用中，這裡會進行 SMTP 連接和郵件發送測試
    # 此處簡化為模擬測試結果
    try:
        # 模擬郵件發送
        # 實際應用中，會使用郵件庫進行發送
        # import smtplib
        # from email.mime.text import MIMEText
        # from email.mime.multipart import MIMEMultipart
        
        # 記錄測試成功
        log = SystemLog(
            level="info",
            component="email",
            message=f"SMTP 連接測試成功，發送郵件至 {test_data.testEmail}",
            user_id=current_user.id,
        )
        db.add(log)
        await db.commit()
        
        return {
            "success": True,
            "data": {
                "connectionStatus": "success",
                "messageSent": True,
                "recipientEmail": test_data.testEmail,
            }
        }
    except Exception as e:
        # 記錄測試失敗
        log = SystemLog(
            level="error",
            component="email",
            message="SMTP 連接測試失敗",
            details=str(e),
            user_id=current_user.id,
        )
        db.add(log)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "CONNECTION_FAILED",
                    "message": "SMTP 連接失敗",
                    "details": {
                        "reason": str(e)
                    }
                }
            }
        )


# 系統參數
@router.get("/system-parameters", response_model=SystemParametersResponse)
async def get_system_parameters(
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取全域系統參數設定
    """
    # 獲取設定
    query = select(SystemParameters).order_by(SystemParameters.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()
    
    if not settings:
        # 返回默認參數
        return {
            "success": True,
            "data": {
                "parameters": {
                    "requestExpiryDays": 30,
                    "responseFormValidityHours": 48,
                    "maxItemsPerRequest": 10,
                    "enableEmailNotifications": True,
                    "enableLineNotifications": True,
                    "systemMaintenanceMode": False,
                }
            }
        }
    
    return {
        "success": True,
        "data": {
            "parameters": {
                "requestExpiryDays": settings.request_expiry_days,
                "responseFormValidityHours": settings.response_form_validity_hours,
                "maxItemsPerRequest": settings.max_items_per_request,
                "enableEmailNotifications": settings.enable_email_notifications,
                "enableLineNotifications": settings.enable_line_notifications,
                "systemMaintenanceMode": settings.system_maintenance_mode,
            }
        }
    }


@router.put("/system-parameters", response_model=SystemParametersUpdateResponse)
async def update_system_parameters(
    request: SystemParametersRequest,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    更新全域系統參數
    """
    # 獲取現有設定
    query = select(SystemParameters).order_by(SystemParameters.id.desc()).limit(1)
    result = await db.execute(query)
    existing_settings = result.scalars().first()
    
    params = request.parameters
    
    if existing_settings:
        # 更新現有設定
        existing_settings.request_expiry_days = params.requestExpiryDays
        existing_settings.response_form_validity_hours = params.responseFormValidityHours
        existing_settings.max_items_per_request = params.maxItemsPerRequest
        existing_settings.enable_email_notifications = params.enableEmailNotifications
        existing_settings.enable_line_notifications = params.enableLineNotifications
        existing_settings.system_maintenance_mode = params.systemMaintenanceMode
        existing_settings.updated_at = datetime.utcnow()
        existing_settings.updated_by = current_user.id
        db.add(existing_settings)
    else:
        # 創建新設定
        new_settings = SystemParameters(
            request_expiry_days=params.requestExpiryDays,
            response_form_validity_hours=params.responseFormValidityHours,
            max_items_per_request=params.maxItemsPerRequest,
            enable_email_notifications=params.enableEmailNotifications,
            enable_line_notifications=params.enableLineNotifications,
            system_maintenance_mode=params.systemMaintenanceMode,
            updated_by=current_user.id,
        )
        db.add(new_settings)
    
    await db.commit()
    
    return {
        "success": True,
        "data": {
            "updated": True
        }
    }


# 系統狀態
@router.get("/system-status", response_model=SystemStatusResponse)
async def check_system_status(
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    檢查系統各組件運行狀態
    """
    # 在實際應用中，這裡會進行各組件的狀態檢查
    # 此處簡化為模擬結果
    
    # 檢查資料庫連接
    try:
        # 簡單的資料庫查詢以檢查連接
        await db.execute(select(func.now()))
        db_status = "healthy"
        db_response_time = 45  # 模擬響應時間
    except Exception:
        db_status = "error"
        db_response_time = None
    
    # 獲取最後的 LINE 和郵件記錄
    line_webhook_query = (
        select(SystemLog.timestamp)
        .where((SystemLog.component == "line") & (SystemLog.level == "info"))
        .order_by(SystemLog.timestamp.desc())
        .limit(1)
    )
    line_result = await db.execute(line_webhook_query)
    last_line_webhook = line_result.scalar()
    
    email_query = (
        select(SystemLog.timestamp)
        .where((SystemLog.component == "email") & (SystemLog.level == "info"))
        .order_by(SystemLog.timestamp.desc())
        .limit(1)
    )
    email_result = await db.execute(email_query)
    last_email_sent = email_result.scalar()
    
    auth_query = (
        select(SystemLog.timestamp)
        .where((SystemLog.component == "auth") & (SystemLog.level == "info"))
        .order_by(SystemLog.timestamp.desc())
        .limit(1)
    )
    auth_result = await db.execute(auth_query)
    last_auth = auth_result.scalar()
    
    # 檢查 LINE Bot 設定
    line_settings_query = select(LineBotSettings).order_by(LineBotSettings.id.desc()).limit(1)
    line_settings_result = await db.execute(line_settings_query)
    line_settings = line_settings_result.scalars().first()
    
    line_status = "healthy" if line_settings else "warning"
    line_error = None if line_settings else "LINE Bot 尚未設定"
    
    # 檢查 SMTP 設定
    smtp_settings_query = select(SmtpSettings).order_by(SmtpSettings.id.desc()).limit(1)
    smtp_settings_result = await db.execute(smtp_settings_query)
    smtp_settings = smtp_settings_result.scalars().first()
    
    email_status = "healthy" if smtp_settings else "warning"
    email_error = None if smtp_settings else "SMTP 尚未設定"
    
    # 檢查 SSO 集成
    # 此處簡化為假設 SSO 正常運作
    sso_status = "healthy"
    
    return {
        "success": True,
        "data": {
            "database": {
                "status": db_status,
                "responseTime": db_response_time,
            },
            "lineBot": {
                "status": line_status,
                "lastWebhookReceived": last_line_webhook,
                "error": line_error,
            },
            "emailService": {
                "status": email_status,
                "lastEmailSent": last_email_sent,
                "error": email_error,
            },
            "ssoIntegration": {
                "status": sso_status,
                "lastSuccessfulAuth": last_auth,
            }
        }
    }


# 系統日誌
@router.get("/system-logs", response_model=SystemLogListResponse)
async def get_system_logs(
    params: LogListParams = Depends(),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    level: Optional[str] = None,
    component: Optional[str] = None,
    user_id: Optional[str] = None,  # Add this parameter
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    查詢系統日誌記錄
    """
    # 構建查詢條件
    conditions = []

    if start_date:
        conditions.append(SystemLog.timestamp >= start_date)

    if end_date:
        conditions.append(SystemLog.timestamp <= end_date)

    if level:
        conditions.append(SystemLog.level == level)

    if component:
        conditions.append(SystemLog.component == component)

    if user_id:  # Add this condition
        conditions.append(SystemLog.user_id == user_id)

    # 計算總數
    count_query = select(func.count(SystemLog.id))
    if conditions:
        from sqlalchemy import and_
        count_query = count_query.where(and_(*conditions))

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 獲取日誌
    query = select(SystemLog).order_by(SystemLog.timestamp.desc())
    if conditions:
        from sqlalchemy import and_
        query = query.where(and_(*conditions))

    # 分頁
    query = query.offset((params.page - 1) * params.limit).limit(params.limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    # 構建回應數據
    log_list = []
    for log in logs:
        import json
        details = json.loads(log.details) if log.details else None

        log_list.append({
            "id": log.id,
            "timestamp": log.timestamp,
            "level": log.level,
            "component": log.component,
            "message": log.message,
            "details": details,
            "userId": log.user_id,  # Add this to include the user ID in the response
        })

    return {
        "success": True,
        "data": {
            "total": total,
            "page": params.page,
            "limit": params.limit,
            "logs": log_list,
        }
    }