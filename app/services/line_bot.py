import json
from typing import Dict, List, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import LineBotSettings
from app.models.settings import SystemLog

class LineBotService:
    """
    LINE Bot 服務
    處理與 LINE 平台的通訊和通知
    """
    
    @staticmethod
    async def get_settings(db: AsyncSession) -> Optional[LineBotSettings]:
        """
        獲取 LINE Bot 設定
        """
        query = select(LineBotSettings).order_by(LineBotSettings.id.desc()).limit(1)
        result = await db.execute(query)
        return result.scalars().first()
    
    @classmethod
    async def send_building_request_notification(
        cls, db: AsyncSession, request_id: str, form_url: str
    ) -> bool:
        """
        發送大樓管理員請求填表通知
        
        Args:
            db: 資料庫連接
            request_id: 申請ID
            form_url: 填表連結
            
        Returns:
            bool: 是否發送成功
        """
        settings = await cls.get_settings(db)
        if not settings:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="line",
                message=f"LINE Bot 設定不存在，無法發送大樓管理員請求填表通知",
                details=json.dumps({"requestId": request_id}),
            )
            db.add(log)
            await db.commit()
            return False
        
        try:
            # 實際應用中，這裡會使用 LINE Bot SDK 發送訊息
            # 此處簡化為模擬發送
            message = settings.building_request_template.replace("{{formUrl}}", form_url)
            
            # 模擬發送
            # from linebot import LineBotApi
            # from linebot.models import TextSendMessage
            # line_bot_api = LineBotApi(settings.channel_access_token)
            # line_bot_api.broadcast(TextSendMessage(text=message))
            
            # 記錄成功
            log = SystemLog(
                level="info",
                component="line",
                message=f"發送大樓管理員請求填表通知成功",
                details=json.dumps({
                    "requestId": request_id,
                    "formUrl": form_url,
                }),
            )
            db.add(log)
            await db.commit()
            
            return True
        except Exception as e:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="line",
                message=f"發送大樓管理員請求填表通知失敗",
                details=json.dumps({
                    "requestId": request_id,
                    "formUrl": form_url,
                    "error": str(e),
                }),
            )
            db.add(log)
            await db.commit()
            
            return False
    
    @classmethod
    async def send_allocation_complete_notification(
        cls, db: AsyncSession, request_id: str, building_name: str
    ) -> bool:
        """
        發送分配完成通知
        
        Args:
            db: 資料庫連接
            request_id: 申請ID
            building_name: 大樓名稱
            
        Returns:
            bool: 是否發送成功
        """
        settings = await cls.get_settings(db)
        if not settings:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="line",
                message=f"LINE Bot 設定不存在，無法發送分配完成通知",
                details=json.dumps({"requestId": request_id, "buildingName": building_name}),
            )
            db.add(log)
            await db.commit()
            return False
        
        try:
            # 實際應用中，這裡會使用 LINE Bot SDK 發送訊息
            # 此處簡化為模擬發送
            message = settings.allocation_complete_template\
                .replace("{{buildingName}}", building_name)\
                .replace("{{requestId}}", request_id)
            
            # 模擬發送
            # from linebot import LineBotApi
            # from linebot.models import TextSendMessage
            # line_bot_api = LineBotApi(settings.channel_access_token)
            # line_bot_api.broadcast(TextSendMessage(text=message))
            
            # 記錄成功
            log = SystemLog(
                level="info",
                component="line",
                message=f"發送分配完成通知成功",
                details=json.dumps({
                    "requestId": request_id,
                    "buildingName": building_name,
                }),
            )
            db.add(log)
            await db.commit()
            
            return True
        except Exception as e:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="line",
                message=f"發送分配完成通知失敗",
                details=json.dumps({
                    "requestId": request_id,
                    "buildingName": building_name,
                    "error": str(e),
                }),
            )
            db.add(log)
            await db.commit()
            
            return False

# 創建服務實例
line_bot_service = LineBotService()