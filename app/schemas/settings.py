from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, EmailStr, field_validator

from app.schemas import ResponseBase, PaginationParams


# 使用者管理
class UserListParams(PaginationParams):
    query: Optional[str] = Field(None, description="搜尋關鍵字")
    role: Optional[str] = Field(None, description="角色過濾")
    sortBy: Optional[str] = Field("createdAt", description="排序欄位")
    sortOrder: Optional[str] = Field("desc", description="排序方向")


class UserListItem(BaseModel):
    userId: str = Field(..., description="使用者ID")
    username: str = Field(..., description="使用者名稱")
    roles: List[str] = Field(..., description="角色清單")
    createdAt: datetime = Field(..., description="建立時間")


class UserListResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "total": 35,
            "page": 1,
            "limit": 20,
            "users": [
                {
                    "userId": "admin001",
                    "username": "Admin User",
                    "roles": ["system_admin"],
                    "createdAt": "2025-01-10T12:00:00Z",
                }
            ],
        },
    )


class UserRoleManage(BaseModel):
    action: str = Field(..., description="操作類型 (grant/revoke)")
    role: str = Field(..., description="角色 (academic_staff/system_admin)")

    @field_validator("action")
    def validate_action(cls, v):
        if v not in ["grant", "revoke"]:
            raise ValueError('操作必須為 "grant" 或 "revoke"')
        return v

    @field_validator("role")
    def validate_role(cls, v):
        if v not in ["academic_staff", "system_admin"]:
            raise ValueError('角色必須為 "academic_staff" 或 "system_admin"')
        return v


class UserRoleResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "userId": "staff001",
            "username": "Academic Staff User",
            "roles": ["academic_staff", "system_admin"],
        },
    )


# LINE Bot 設定
class LineBotNotificationTemplate(BaseModel):
    buildingManagerRequest: str = Field(..., description="大樓管理員請求填表的訊息樣板")
    allocationComplete: str = Field(..., description="分配完成的通知訊息樣板")

    @field_validator("buildingManagerRequest")
    def validate_building_manager_template(cls, v):
        if "{{formUrl}}" not in v:
            raise ValueError('樣板必須包含 "{{formUrl}}" 變數')
        return v

    @field_validator("allocationComplete")
    def validate_allocation_template(cls, v):
        if "{{buildingName}}" not in v or "{{requestId}}" not in v:
            raise ValueError('樣板必須包含 "{{buildingName}}" 和 "{{requestId}}" 變數')
        return v


class LineBotSettingsSchema(BaseModel):
    """
    Pydantic schema for LINE Bot settings - used as input model
    """
    channelAccessToken: str = Field(..., description="Channel Access Token")
    targetId: str = Field(..., description="Target User ID or Group ID")
    notificationTemplates: LineBotNotificationTemplate = Field(..., description="通知訊息樣板")


# Alias the class for backwards compatibility and to avoid confusion with database model
LineBotSettings = LineBotSettingsSchema


class LineBotSettingsResponse(ResponseBase):
    data: dict = Field(
        ..., 
        example={
            "channelAccessToken": "encrypted_token_placeholder",
            "targetId": "U1234567890abcdef1234567890abcdef",
            "notificationTemplates": {
                "buildingManagerRequest": "您好，NTUNHS設備借用系統有新的借用申請需要回應。請點擊以下連結填寫可提供的器材數量：{{formUrl}}",
                "allocationComplete": "{{buildingName}}大樓管理員，NTUNHS設備借用系統已完成器材分配，請協助準備借用申請{{requestId}}的器材。",
            }
        }
    )


class LineBotSettingsUpdateResponse(ResponseBase):
    data: dict = Field(..., example={"updated": True})


class LineBotTestResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "connectionStatus": "success",
            "botInfo": {"targetId": "U1234567890abcdef1234567890abcdef"},
        },
    )


# SMTP 設定
class EmailTemplate(BaseModel):
    subject: str = Field(..., description="郵件主旨")
    body: str = Field(..., description="郵件內容")


class EmailTemplates(BaseModel):
    approvalNotification: EmailTemplate = Field(..., description="核准通知郵件樣板")

    @field_validator("approvalNotification")
    def validate_approval_template(cls, v):
        if "{{requestId}}" not in v.subject:
            raise ValueError('主旨必須包含 "{{requestId}}" 變數')
        if "{{username}}" not in v.body:
            raise ValueError('內容必須包含 "{{username}}" 變數')
        return v


class SmtpSettings(BaseModel):
    host: str = Field(..., description="SMTP 主機地址")
    port: int = Field(..., gt=0, lt=65536, description="SMTP 端口")
    secure: bool = Field(..., description="是否使用 SSL/TLS")
    username: str = Field(..., description="SMTP 帳號")
    password: str = Field(..., description="SMTP 密碼")
    senderEmail: EmailStr = Field(..., description="寄件者電子郵件")
    senderName: str = Field(..., description="寄件者名稱")
    emailTemplates: EmailTemplates = Field(..., description="郵件樣板")


class SmtpSettingsResponse(ResponseBase):
    data: SmtpSettings


class SmtpSettingsUpdateResponse(ResponseBase):
    data: dict = Field(..., example={"updated": True})


class SmtpTestRequest(BaseModel):
    testEmail: EmailStr = Field(..., description="測試郵箱")


class SmtpTestResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "connectionStatus": "success",
            "messageSent": True,
            "recipientEmail": "test@example.com",
        },
    )


# 系統參數
class SystemParameters(BaseModel):
    requestExpiryDays: int = Field(..., gt=0, description="申請過期天數")
    responseFormValidityHours: int = Field(..., gt=0, description="填表連結有效小時數")
    maxItemsPerRequest: int = Field(..., gt=0, description="每個申請最多可包含的項目數")
    enableEmailNotifications: bool = Field(..., description="是否啟用電子郵件通知")
    enableLineNotifications: bool = Field(..., description="是否啟用 LINE 通知")
    systemMaintenanceMode: bool = Field(..., description="系統維護模式")


class SystemParametersRequest(BaseModel):
    parameters: SystemParameters = Field(..., description="系統參數")


class SystemParametersResponse(ResponseBase):
    data: dict = Field(..., example={"parameters": {}})


class SystemParametersUpdateResponse(ResponseBase):
    data: dict = Field(..., example={"updated": True})


# 系統狀態
class SystemComponentStatus(BaseModel):
    status: str = Field(..., description="狀態 (healthy/warning/error)")
    responseTime: Optional[int] = Field(None, description="回應時間 (毫秒)")
    lastWebhookReceived: Optional[datetime] = Field(None, description="最後 Webhook 接收時間")
    lastEmailSent: Optional[datetime] = Field(None, description="最後郵件發送時間")
    lastSuccessfulAuth: Optional[datetime] = Field(None, description="最後成功認證時間")
    error: Optional[str] = Field(None, description="錯誤訊息")


class SystemStatus(BaseModel):
    database: SystemComponentStatus = Field(..., description="資料庫狀態")
    lineBot: SystemComponentStatus = Field(..., description="LINE Bot 狀態")
    emailService: SystemComponentStatus = Field(..., description="電子郵件服務狀態")
    ssoIntegration: SystemComponentStatus = Field(..., description="SSO 整合狀態")


class SystemStatusResponse(ResponseBase):
    data: SystemStatus


# 系統日誌
class LogListParams(PaginationParams):
    startDate: Optional[datetime] = Field(None, description="開始日期")
    endDate: Optional[datetime] = Field(None, description="結束日期")
    level: Optional[str] = Field(None, description="日誌級別 (info/warning/error)")
    component: Optional[str] = Field(None, description="系統組件 (auth/request/email/line)")


class SystemLogItem(BaseModel):
    id: str = Field(..., description="日誌ID")
    timestamp: datetime = Field(..., description="時間戳")
    level: str = Field(..., description="日誌級別")
    component: str = Field(..., description="系統組件")
    message: str = Field(..., description="日誌訊息")
    details: Optional[Dict[str, Any]] = Field(None, description="詳細資訊")
    userId: Optional[str] = Field(None, description="使用者ID")
    ipAddress: Optional[str] = Field(None, description="IP地址")

class SystemLogListResponse(ResponseBase):
    data: dict = Field(
        ...,
        example={
            "total": 1354,
            "page": 1,
            "limit": 50,
            "logs": [
                {
                    "id": "log_001",
                    "timestamp": "2025-04-27T16:45:22Z",
                    "level": "info",
                    "component": "request",
                    "message": "新申請已創建: req_123456",
                    "details": {
                        "userId": "user123",
                        "requestId": "req_123456",
                    },
                    "userId": "user123",
                    "ipAddress": "192.168.1.100"
                }
            ],
        },
    )