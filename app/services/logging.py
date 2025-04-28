import json
from datetime import datetime
from typing import Dict, Any, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.models.settings import SystemLog


class LoggingService:
    """
    統一的系統日誌服務
    提供記錄各種系統事件的方法
    """

    @staticmethod
    async def log(
        db: AsyncSession,
        level: str,
        component: str,
        message: str,
        details: Optional[Union[Dict[str, Any], str]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> SystemLog:
        """
        記錄系統日誌

        Args:
            db: 資料庫連接
            level: 日誌級別 (info, warning, error)
            component: 系統組件 (auth, request, email, line, admin, building, equipment, allocation, response, system)
            message: 日誌訊息
            details: 詳細資訊 (可選)
            user_id: 使用者ID (可選)
            request_id: 申請ID (可選)
            ip_address: IP地址 (可選)

        Returns:
            SystemLog: 創建的日誌記錄
        """
        # 將詳細資訊轉換為JSON字符串
        if details and isinstance(details, dict):
            details_json = json.dumps(details)
        elif details:
            details_json = str(details)
        else:
            details_json = None

        # 創建日誌記錄
        log = SystemLog(
            level=level,
            component=component,
            message=message,
            details=details_json,
            user_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
        )

        db.add(log)
        await db.commit()
        return log

    @classmethod
    async def info(
        cls,
        db: AsyncSession,
        component: str,
        message: str,
        details: Optional[Union[Dict[str, Any], str]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> SystemLog:
        """記錄信息級別日誌"""
        return await cls.log(
            db=db,
            level="info",
            component=component,
            message=message,
            details=details,
            user_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
        )

    @classmethod
    async def warning(
        cls,
        db: AsyncSession,
        component: str,
        message: str,
        details: Optional[Union[Dict[str, Any], str]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> SystemLog:
        """記錄警告級別日誌"""
        return await cls.log(
            db=db,
            level="warning",
            component=component,
            message=message,
            details=details,
            user_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
        )

    @classmethod
    async def error(
        cls,
        db: AsyncSession,
        component: str,
        message: str,
        details: Optional[Union[Dict[str, Any], str]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> SystemLog:
        """記錄錯誤級別日誌"""
        return await cls.log(
            db=db,
            level="error",
            component=component,
            message=message,
            details=details,
            user_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
        )

    @classmethod
    async def audit(
        cls,
        db: AsyncSession,
        component: str,
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> SystemLog:
        """
        記錄審計日誌（用於記錄操作行為）

        Args:
            db: 資料庫連接
            component: 系統組件
            action: 操作類型 (create, update, delete, login, logout等)
            user_id: 操作者ID
            resource_type: 資源類型 (request, equipment, building等)
            resource_id: 資源ID
            details: 詳細資訊 (可選)
            ip_address: IP地址 (可選)

        Returns:
            SystemLog: 創建的日誌記錄
        """
        message = f"{action.upper()} {resource_type} {resource_id}"
        
        audit_details = {
            "action": action,
            "resourceType": resource_type,
            "resourceId": resource_id,
        }
        
        if details:
            audit_details.update(details)
            
        return await cls.info(
            db=db,
            component=component,
            message=message,
            details=audit_details,
            user_id=user_id,
            ip_address=ip_address,
        )

    @classmethod
    async def get_request_ip(cls, request: Request) -> str:
        """從請求中獲取客戶端IP地址"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host


# 創建服務實例
logging_service = LoggingService()