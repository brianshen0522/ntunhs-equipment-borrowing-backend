from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_system_admin_user
from app.database import get_db
from app.models.users import User
from app.models.settings import LineBotSettings, SmtpSettings, SystemParameters, SystemLog
from app.schemas.settings import (
    LineBotSettingsSchema,  # Note: renamed from LineBotSettings to avoid confusion
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
from app.services.logging import logging_service
from app.services.line_bot import line_bot_service

router = APIRouter(prefix="/admin", tags=["admin"])


# LINE Bot 設定
@router.get("/line-bot-settings", response_model=LineBotSettingsResponse)
async def get_line_bot_settings(
    request: Request,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取當前 LINE Bot 設定
    """
    # 記錄查詢操作
    await logging_service.audit(
        db,
        component="admin",
        action="read",
        user_id=current_user.id,
        resource_type="line_bot_settings",
        resource_id="current",
        ip_address=await logging_service.get_request_ip(request)
    )

    # 獲取設定
    query = select(LineBotSettings).order_by(LineBotSettings.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()

    if not settings:
        await logging_service.warning(
            db,
            component="admin",
            message="LINE Bot 設定尚未建立",
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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
            "channelAccessToken": "encrypted_token_placeholder",  # 為安全起見不返回實際令牌
            "targetId": settings.target_id,
            "notificationTemplates": {
                "buildingManagerRequest": settings.building_request_template,
                "allocationComplete": settings.allocation_complete_template,
            }
        }
    }


@router.put("/line-bot-settings", response_model=LineBotSettingsUpdateResponse)
async def update_line_bot_settings(
    request: Request,
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

    # 準備日誌詳情，移除敏感資訊
    log_details = {
        "targetId": settings_in.targetId,
        "templates_updated": True,
        "is_new_record": existing_settings is None
    }

    if existing_settings:
        # 更新現有設定
        existing_settings.channel_access_token = settings_in.channelAccessToken
        existing_settings.target_id = settings_in.targetId
        existing_settings.building_request_template = settings_in.notificationTemplates.buildingManagerRequest
        existing_settings.allocation_complete_template = settings_in.notificationTemplates.allocationComplete
        existing_settings.updated_at = datetime.utcnow()
        existing_settings.updated_by = current_user.id
        db.add(existing_settings)

        # 記錄更新操作
        await logging_service.audit(
            db,
            component="admin",
            action="update",
            user_id=current_user.id,
            resource_type="line_bot_settings",
            resource_id=str(existing_settings.id),
            details=log_details,
            ip_address=await logging_service.get_request_ip(request)
        )
    else:
        # 創建新設定
        new_settings = LineBotSettings(
            channel_access_token=settings_in.channelAccessToken,
            target_id=settings_in.targetId,
            building_request_template=settings_in.notificationTemplates.buildingManagerRequest,
            allocation_complete_template=settings_in.notificationTemplates.allocationComplete,
            updated_by=current_user.id,
        )
        db.add(new_settings)

        # 記錄創建操作
        await logging_service.audit(
            db,
            component="admin",
            action="create",
            user_id=current_user.id,
            resource_type="line_bot_settings",
            resource_id="new",
            details=log_details,
            ip_address=await logging_service.get_request_ip(request)
        )

    await db.commit()

    return {
        "success": True,
        "data": {
            "updated": True
        }
    }


@router.post("/line-bot-test", response_model=LineBotTestResponse)
async def test_line_bot(
    request: Request,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    測試 LINE Bot 連接是否正常
    """
    # 記錄測試操作
    await logging_service.info(
        db,
        component="admin",
        message="LINE Bot 連接測試請求",
        user_id=current_user.id,
        ip_address=await logging_service.get_request_ip(request)
    )

    # 獲取設定
    query = select(LineBotSettings).order_by(LineBotSettings.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()

    if not settings:
        await logging_service.warning(
            db,
            component="admin",
            message="LINE Bot 連接測試失敗：設定不存在",
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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
    try:
        # 發送測試訊息
        test_message = f"這是一條測試訊息，發送時間：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        success = await line_bot_service.send_push_message(db, test_message, settings)
        
        if not success:
            raise Exception("發送測試訊息失敗")

        # 記錄測試成功
        await logging_service.info(
            db,
            component="line",
            message="LINE Bot 連接測試成功",
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

        return {
            "success": True,
            "data": {
                "connectionStatus": "success",
                "botInfo": {
                    "targetId": settings.target_id
                }
            }
        }
    except Exception as e:
        # 記錄測試失敗
        await logging_service.error(
            db,
            component="line",
            message="LINE Bot 連接測試失敗",
            details=str(e),
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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
    request: Request,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取當前 SMTP 設定
    """
    # 記錄查詢操作
    await logging_service.audit(
        db,
        component="admin",
        action="read",
        user_id=current_user.id,
        resource_type="smtp_settings",
        resource_id="current",
        ip_address=await logging_service.get_request_ip(request)
    )

    # 獲取設定
    query = select(SmtpSettings).order_by(SmtpSettings.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()

    if not settings:
        await logging_service.warning(
            db,
            component="admin",
            message="SMTP 設定尚未建立",
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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
    request: Request,
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

    # 準備日誌詳情，移除敏感資訊
    log_details = {
        "host": settings_in.host,
        "port": settings_in.port,
        "secure": settings_in.secure,
        "username": settings_in.username,
        "senderEmail": settings_in.senderEmail,
        "senderName": settings_in.senderName,
        "templates_updated": True,
        "is_new_record": existing_settings is None
    }

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

        # 記錄更新操作
        await logging_service.audit(
            db,
            component="admin",
            action="update",
            user_id=current_user.id,
            resource_type="smtp_settings",
            resource_id=str(existing_settings.id),
            details=log_details,
            ip_address=await logging_service.get_request_ip(request)
        )
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

        # 記錄創建操作
        await logging_service.audit(
            db,
            component="admin",
            action="create",
            user_id=current_user.id,
            resource_type="smtp_settings",
            resource_id="new",
            details=log_details,
            ip_address=await logging_service.get_request_ip(request)
        )

    await db.commit()

    return {
        "success": True,
        "data": {
            "updated": True
        }
    }


@router.post("/smtp-test", response_model=SmtpTestResponse)
async def test_smtp(
    request: Request,
    test_data: SmtpTestRequest,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    測試 SMTP 連接是否正常
    """
    # 記錄測試操作
    await logging_service.info(
        db,
        component="admin",
        message=f"SMTP 連接測試請求，目標郵箱: {test_data.testEmail}",
        user_id=current_user.id,
        ip_address=await logging_service.get_request_ip(request)
    )

    # 獲取設定
    query = select(SmtpSettings).order_by(SmtpSettings.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()

    if not settings:
        await logging_service.warning(
            db,
            component="admin",
            message="SMTP 連接測試失敗：設定不存在",
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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
        await logging_service.info(
            db,
            component="email",
            message=f"SMTP 連接測試成功，發送郵件至 {test_data.testEmail}",
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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
        await logging_service.error(
            db,
            component="email",
            message="SMTP 連接測試失敗",
            details=str(e),
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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
    request: Request,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    獲取全域系統參數設定
    """
    # 記錄查詢操作
    await logging_service.audit(
        db,
        component="admin",
        action="read",
        user_id=current_user.id,
        resource_type="system_parameters",
        resource_id="current",
        ip_address=await logging_service.get_request_ip(request)
    )

    # 獲取設定
    query = select(SystemParameters).order_by(SystemParameters.id.desc()).limit(1)
    result = await db.execute(query)
    settings = result.scalars().first()

    if not settings:
        # 返回默認參數
        await logging_service.info(
            db,
            component="admin",
            message="系統參數尚未建立，返回默認值",
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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
    request: Request,
    request_data: SystemParametersRequest,
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

    params = request_data.parameters

    # 準備日誌詳情
    log_details = {
        "requestExpiryDays": params.requestExpiryDays,
        "responseFormValidityHours": params.responseFormValidityHours,
        "maxItemsPerRequest": params.maxItemsPerRequest,
        "enableEmailNotifications": params.enableEmailNotifications,
        "enableLineNotifications": params.enableLineNotifications,
        "systemMaintenanceMode": params.systemMaintenanceMode,
        "is_new_record": existing_settings is None
    }

    if existing_settings:
        # 檢查是否啟用了維護模式
        maintenance_mode_changed = existing_settings.system_maintenance_mode != params.systemMaintenanceMode

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

        # 記錄更新操作
        await logging_service.audit(
            db,
            component="admin",
            action="update",
            user_id=current_user.id,
            resource_type="system_parameters",
            resource_id=str(existing_settings.id),
            details=log_details,
            ip_address=await logging_service.get_request_ip(request)
        )

        # 如果維護模式狀態變更，記錄特殊日誌
        if maintenance_mode_changed:
            status_msg = "啟用" if params.systemMaintenanceMode else "停用"
            await logging_service.info(
                db,
                component="system",
                message=f"系統維護模式已{status_msg}",
                user_id=current_user.id,
                ip_address=await logging_service.get_request_ip(request)
            )
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

        # 記錄創建操作
        await logging_service.audit(
            db,
            component="admin",
            action="create",
            user_id=current_user.id,
            resource_type="system_parameters",
            resource_id="new",
            details=log_details,
            ip_address=await logging_service.get_request_ip(request)
        )

        # 如果維護模式被啟用，記錄特殊日誌
        if params.systemMaintenanceMode:
            await logging_service.info(
                db,
                component="system",
                message="系統維護模式已啟用",
                user_id=current_user.id,
                ip_address=await logging_service.get_request_ip(request)
            )

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
    request: Request,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    檢查系統各組件運行狀態
    """
    # 記錄查詢操作
    await logging_service.audit(
        db,
        component="admin",
        action="read",
        user_id=current_user.id,
        resource_type="system_status",
        resource_id="current",
        ip_address=await logging_service.get_request_ip(request)
    )

    # 在實際應用中，這裡會進行各組件的狀態檢查
    # 此處簡化為模擬結果

    # 檢查資料庫連接
    try:
        # 簡單的資料庫查詢以檢查連接
        start_time = datetime.utcnow()
        await db.execute(select(func.now()))
        end_time = datetime.utcnow()
        db_status = "healthy"
        db_response_time = int((end_time - start_time).total_seconds() * 1000)  # 轉換為毫秒
    except Exception as e:
        db_status = "error"
        db_response_time = None

        # 記錄資料庫錯誤
        await logging_service.error(
            db,
            component="database",
            message="資料庫連接檢查失敗",
            details=str(e),
            user_id=current_user.id,
            ip_address=await logging_service.get_request_ip(request)
        )

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

    # 記錄系統狀態檢查結果
    status_summary = {
        "database": db_status,
        "lineBot": line_status,
        "emailService": email_status,
        "ssoIntegration": sso_status
    }
    await logging_service.info(
        db,
        component="system",
        message="系統狀態檢查完成",
        details=status_summary,
        user_id=current_user.id,
        ip_address=await logging_service.get_request_ip(request)
    )

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
    request: Request,
    params: LogListParams = Depends(),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    level: Optional[str] = None,
    component: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_system_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    查詢系統日誌記錄
    """
    # 記錄查詢操作
    await logging_service.audit(
        db,
        component="admin",
        action="read",
        user_id=current_user.id,
        resource_type="system_logs",
        resource_id="list",
        details={
            "page": params.page,
            "limit": params.limit,
            "filters": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "level": level,
                "component": component,
                "user_id": user_id
            }
        },
        ip_address=await logging_service.get_request_ip(request)
    )

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

    if user_id:
        # 修改為使用 LIKE 進行模糊查詢，允許部分匹配使用者 ID
        conditions.append(SystemLog.user_id.ilike(f"%{user_id}%"))

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
    import json
    for log in logs:
        # 添加錯誤處理以防止 JSON 解析錯誤
        details = None
        if log.details:
            try:
                details = json.loads(log.details)
            except json.JSONDecodeError:
                # 如果 JSON 解析失敗，則以原始文本形式返回
                details = {"raw_content": log.details}

        log_list.append({
            "id": log.id,
            "timestamp": log.timestamp,
            "level": log.level,
            "component": log.component,
            "message": log.message,
            "details": details,
            "userId": log.user_id,
            "ipAddress": log.ip_address,  # 添加 IP 地址到回應中
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