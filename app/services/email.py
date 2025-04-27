import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import SmtpSettings
from app.models.settings import SystemLog
from app.models.requests import Request
from app.models.users import User

class EmailService:
    """
    電子郵件服務
    處理與 SMTP 伺服器的通訊和郵件發送
    """
    
    @staticmethod
    async def get_settings(db: AsyncSession) -> Optional[SmtpSettings]:
        """
        獲取 SMTP 設定
        """
        query = select(SmtpSettings).order_by(SmtpSettings.id.desc()).limit(1)
        result = await db.execute(query)
        return result.scalars().first()
    
    @classmethod
    async def send_approval_notification(
        cls, 
        db: AsyncSession, 
        request_id: str, 
        user_email: str, 
        username: str,
        pdf_path: Optional[str] = None
    ) -> bool:
        """
        發送核准通知郵件
        
        Args:
            db: 資料庫連接
            request_id: 申請ID
            user_email: 使用者電子郵件
            username: 使用者名稱
            pdf_path: PDF文件路徑 (可選)
            
        Returns:
            bool: 是否發送成功
        """
        settings = await cls.get_settings(db)
        if not settings:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="email",
                message=f"SMTP 設定不存在，無法發送核准通知郵件",
                details=json.dumps({"requestId": request_id, "recipient": user_email}),
            )
            db.add(log)
            await db.commit()
            return False
        
        try:
            # 解析郵件樣板
            email_templates = json.loads(settings.email_templates)
            template = email_templates.get("approvalNotification", {})
            
            subject = template.get("subject", "器材借用申請已核准").replace("{{requestId}}", request_id)
            body = template.get("body", "您的器材借用申請已核准。").replace("{{username}}", username)
            
            # 實際應用中，這裡會使用郵件庫發送郵件
            # 此處簡化為模擬發送
            # import smtplib
            # from email.mime.text import MIMEText
            # from email.mime.multipart import MIMEMultipart
            # from email.mime.application import MIMEApplication
            
            # 模擬發送
            # server = smtplib.SMTP(settings.host, settings.port)
            # server.starttls()
            # server.login(settings.username, settings.password)
            # server.sendmail(settings.sender_email, user_email, message.as_string())
            # server.quit()
            
            # 記錄成功
            log = SystemLog(
                level="info",
                component="email",
                message=f"發送核准通知郵件成功",
                details=json.dumps({
                    "requestId": request_id,
                    "recipient": user_email,
                    "hasPdf": pdf_path is not None,
                }),
            )
            db.add(log)
            await db.commit()
            
            return True
        except Exception as e:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="email",
                message=f"發送核准通知郵件失敗",
                details=json.dumps({
                    "requestId": request_id,
                    "recipient": user_email,
                    "error": str(e),
                }),
            )
            db.add(log)
            await db.commit()
            
            return False
    
    @classmethod
    async def send_request_approved_email(cls, db: AsyncSession, request_id: str) -> bool:
        """
        發送申請已核准通知郵件
        
        Args:
            db: 資料庫連接
            request_id: 申請ID
            
        Returns:
            bool: 是否發送成功
        """
        # 獲取申請和用戶信息
        query = (
            select(Request, User.email, User.username)
            .join(User, Request.user_id == User.id)
            .where(Request.id == request_id)
        )
        result = await db.execute(query)
        request_data = result.first()
        
        if not request_data:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="email",
                message=f"找不到申請，無法發送核准通知郵件",
                details=json.dumps({"requestId": request_id}),
            )
            db.add(log)
            await db.commit()
            return False
        
        request, user_email, username = request_data
        
        # 發送郵件
        success = await cls.send_approval_notification(
            db, 
            request_id, 
            user_email, 
            username, 
            pdf_path=request.pdf_path
        )
        
        if success:
            # 更新已發送郵件標記
            request.email_sent = True
            await db.commit()
        
        return success

# 創建服務實例
email_service = EmailService()