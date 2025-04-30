import json
import httpx
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
    async def send_push_message(
        cls, db: AsyncSession, message: str, settings: Optional[LineBotSettings] = None
    ) -> bool:
        """
        發送LINE推播訊息

        Args:
            db: 資料庫連接
            message: 要發送的訊息
            settings: LINE Bot設定 (可選，若未提供則自動獲取)

        Returns:
            bool: 是否發送成功
        """
        if not settings:
            settings = await cls.get_settings(db)

        if not settings:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="line",
                message=f"LINE Bot 設定不存在，無法發送通知訊息",
                details=json.dumps({"message": message[:100] + "..." if len(message) > 100 else message}),
            )
            db.add(log)
            await db.commit()
            return False

        # 檢查target_id是否存在且有效
        if not settings.target_id or settings.target_id.strip() == "":
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="line",
                message=f"LINE Bot target_id 未設定或無效，無法發送通知訊息",
                details=json.dumps({"message": message[:100] + "..." if len(message) > 100 else message}),
            )
            db.add(log)
            await db.commit()
            return False

        try:
            # 準備請求數據
            push_data = {
                "to": settings.target_id,
                "messages": [
                    {
                        "type": "text",
                        "text": message
                    }
                ]
            }

            # 發送請求到LINE API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.channel_access_token}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.line.me/v2/bot/message/push",
                    json=push_data,
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    # 記錄成功
                    log = SystemLog(
                        level="info",
                        component="line",
                        message=f"發送LINE通知訊息成功",
                        details=json.dumps({
                            "targetId": settings.target_id,
                            "messagePreview": message[:100] + "..." if len(message) > 100 else message
                        }),
                    )
                    db.add(log)
                    await db.commit()
                    return True
                else:
                    # 記錄失敗
                    log = SystemLog(
                        level="error",
                        component="line",
                        message=f"發送LINE通知訊息失敗: HTTP {response.status_code}",
                        details=json.dumps({
                            "targetId": settings.target_id,
                            "messagePreview": message[:100] + "..." if len(message) > 100 else message,
                            "responseBody": response.text
                        }),
                    )
                    db.add(log)
                    await db.commit()
                    return False

        except Exception as e:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="line",
                message=f"發送LINE通知訊息失敗",
                details=json.dumps({
                    "targetId": settings.target_id if settings else "unknown",
                    "messagePreview": message[:100] + "..." if len(message) > 100 else message,
                    "error": str(e)
                }),
            )
            db.add(log)
            await db.commit()
            return False

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

        # 準備訊息
        message = settings.building_request_template.replace("{{formUrl}}", form_url)

        # 記錄發送嘗試
        log = SystemLog(
            level="info",
            component="line",
            message=f"嘗試發送大樓管理員請求填表通知",
            details=json.dumps({
                "requestId": request_id, 
                "formUrl": form_url,
                "targetId": settings.target_id
            })
        )
        db.add(log)
        await db.commit()

        # 發送訊息
        return await cls.send_push_message(db, message, settings)

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

        # 準備訊息
        message = settings.allocation_complete_template.replace("{{buildingName}}", building_name).replace("{{requestId}}", request_id)

        # 記錄發送嘗試
        log = SystemLog(
            level="info",
            component="line",
            message=f"嘗試發送分配完成通知",
            details=json.dumps({
                "requestId": request_id, 
                "buildingName": building_name,
                "targetId": settings.target_id
            })
        )
        db.add(log)
        await db.commit()

        # 發送訊息
        return await cls.send_push_message(db, message, settings)

# 創建服務實例
line_bot_service = LineBotService()