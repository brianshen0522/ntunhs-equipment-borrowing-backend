import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import select, update, and_, or_, join, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crud.base import CRUDBase
from app.models.responses import BuildingResponseToken, BuildingResponse, BuildingResponseItem
from app.models.requests import Request, RequestItem
from app.models.buildings import Building
from app.models.equipment import Equipment
from app.schemas.responses import BuildingResponseCreate


class CRUDResponse(CRUDBase[BuildingResponse, BuildingResponseCreate, Any]):
    """大樓回覆 CRUD 操作類"""

    async def create_token(self, db: AsyncSession, *, request_id: str) -> Optional[BuildingResponseToken]:
        """創建回覆令牌"""
        # 檢查請求是否存在
        query = select(Request).where(Request.id == request_id)
        result = await db.execute(query)
        request = result.scalars().first()
        
        if not request:
            return None
        
        # 創建令牌
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=settings.RESPONSE_FORM_VALIDITY_HOURS)
        
        db_token = BuildingResponseToken(
            id=str(uuid.uuid4()),
            request_id=request_id,
            token=token,
            expires_at=expires_at,
            is_used=False,
        )
        
        db.add(db_token)
        await db.commit()
        await db.refresh(db_token)
        
        return db_token

    async def get_token_by_token(self, db: AsyncSession, *, token: str) -> Optional[BuildingResponseToken]:
        """根據令牌獲取令牌記錄"""
        query = select(BuildingResponseToken).where(BuildingResponseToken.token == token)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_form_data(self, db: AsyncSession, *, token: str) -> Optional[Dict[str, Any]]:
        """獲取填表頁面數據"""
        # 檢查令牌是否有效
        token_query = (
            select(BuildingResponseToken)
            .where(
                and_(
                    BuildingResponseToken.token == token,
                    BuildingResponseToken.expires_at > datetime.utcnow(),
                )
            )
        )
        token_result = await db.execute(token_query)
        token_obj = token_result.scalars().first()
        
        if not token_obj:
            return None
        
        # 獲取申請基本信息
        request_query = select(Request).where(Request.id == token_obj.request_id)
        request_result = await db.execute(request_query)
        request = request_result.scalars().first()
        
        if not request or request.status != "pending_building_response":
            return None
        
        # 獲取申請項目
        items_query = (
            select(RequestItem, Equipment.name.label("equipment_name"))
            .join(Equipment, RequestItem.equipment_id == Equipment.id)
            .where(RequestItem.request_id == token_obj.request_id)
        )
        items_result = await db.execute(items_query)
        
        # 獲取大樓列表
        buildings_query = select(Building).where(Building.enabled == True).order_by(Building.name)
        buildings_result = await db.execute(buildings_query)
        
        # 獲取先前回覆（如果有的話）
        previous_response = None
        previous_building_id = None
        previous_items = []
        
        if token_obj.is_used:
            response_query = (
                select(BuildingResponse)
                .where(BuildingResponse.response_token_id == token_obj.id)
            )
            response_result = await db.execute(response_query)
            previous_response = response_result.scalars().first()
            
            if previous_response:
                previous_building_id = previous_response.building_id
                
                # 獲取回覆項目
                response_items_query = (
                    select(BuildingResponseItem)
                    .where(BuildingResponseItem.response_id == previous_response.id)
                )
                response_items_result = await db.execute(response_items_query)
                for item in response_items_result.scalars().all():
                    previous_items.append({
                        "itemId": item.request_item_id,
                        "availableQuantity": item.available_quantity,
                    })
        
        # 構建返回數據
        items = []
        for item, equipment_name in items_result.all():
            items.append({
                "itemId": item.id,
                "equipmentName": equipment_name,
                "requestedQuantity": item.requested_quantity,
            })
        
        buildings = []
        for building in buildings_result.scalars().all():
            buildings.append({
                "buildingId": building.id,
                "buildingName": building.name,
            })
        
        response_data = {
            "buildingId": previous_building_id,
            "items": previous_items,
        }
        
        return {
            "requestId": request.id,
            "requestDetails": {
                "startDate": request.start_date,
                "endDate": request.end_date,
                "venue": request.venue,
            },
            "items": items,
            "buildings": buildings,
            "responseData": response_data,
        }

    async def submit_response(
        self, db: AsyncSession, *, token: str, obj_in: BuildingResponseCreate, ip_address: Optional[str] = None
    ) -> Optional[BuildingResponse]:
        """提交大樓管理員回覆"""
        # 檢查令牌是否有效
        token_query = (
            select(BuildingResponseToken)
            .where(
                and_(
                    BuildingResponseToken.token == token,
                    BuildingResponseToken.expires_at > datetime.utcnow(),
                )
            )
        )
        token_result = await db.execute(token_query)
        token_obj = token_result.scalars().first()
        
        if not token_obj:
            return None
        
        # 檢查申請是否存在
        request_query = select(Request).where(Request.id == token_obj.request_id)
        request_result = await db.execute(request_query)
        request = request_result.scalars().first()
        
        if not request or request.status != "pending_building_response":
            return None
        
        # 檢查大樓是否存在
        building_query = select(Building).where(
            and_(Building.id == obj_in.buildingId, Building.enabled == True)
        )
        building_result = await db.execute(building_query)
        building = building_result.scalars().first()
        
        if not building:
            return None
        
        # 驗證所有項目是否存在
        for item in obj_in.items:
            item_query = select(RequestItem).where(
                and_(RequestItem.id == item.itemId, RequestItem.request_id == token_obj.request_id)
            )
            item_result = await db.execute(item_query)
            item_obj = item_result.scalars().first()
            
            if not item_obj:
                return None
        
        # 如果令牌已使用，更新現有回覆
        if token_obj.is_used:
            response_query = (
                select(BuildingResponse)
                .where(BuildingResponse.response_token_id == token_obj.id)
            )
            response_result = await db.execute(response_query)
            existing_response = response_result.scalars().first()
            
            if existing_response:
                # 更新大樓
                existing_response.building_id = obj_in.buildingId
                
                # 刪除現有項目
                delete_items_query = (
                    select(BuildingResponseItem)
                    .where(BuildingResponseItem.response_id == existing_response.id)
                )
                delete_items_result = await db.execute(delete_items_query)
                for item in delete_items_result.scalars().all():
                    await db.delete(item)
                
                # 添加新項目
                for item in obj_in.items:
                    db_item = BuildingResponseItem(
                        id=str(uuid.uuid4()),
                        response_id=existing_response.id,
                        request_item_id=item.itemId,
                        available_quantity=item.availableQuantity,
                    )
                    db.add(db_item)
                
                await db.commit()
                await db.refresh(existing_response)
                
                return existing_response
        
        # 創建新回覆
        db_response = BuildingResponse(
            id=str(uuid.uuid4()),
            request_id=token_obj.request_id,
            building_id=obj_in.buildingId,
            response_token_id=token_obj.id,
            ip_address=ip_address,
        )
        db.add(db_response)
        
        # 添加項目
        for item in obj_in.items:
            db_item = BuildingResponseItem(
                id=str(uuid.uuid4()),
                response_id=db_response.id,
                request_item_id=item.itemId,
                available_quantity=item.availableQuantity,
            )
            db.add(db_item)
        
        # 更新令牌狀態
        token_obj.is_used = True
        
        # 更新申請狀態為待分配
        request.status = "pending_allocation"
        request.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(db_response)
        
        return db_response

    async def get_responses(
        self, db: AsyncSession, *, request_id: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """獲取大樓管理員回覆列表"""
        # 檢查申請是否存在
        request_query = select(Request).where(Request.id == request_id)
        request_result = await db.execute(request_query)
        request = request_result.scalars().first()
        
        if not request:
            return [], []
        
        # 獲取回覆列表
        responses_query = (
            select(BuildingResponse, Building.name.label("building_name"))
            .join(Building, BuildingResponse.building_id == Building.id)
            .where(BuildingResponse.request_id == request_id)
            .order_by(BuildingResponse.submitted_at.desc())
        )
        responses_result = await db.execute(responses_query)
        
        # 獲取申請項目
        items_query = (
            select(RequestItem, Equipment.name.label("equipment_name"))
            .join(Equipment, RequestItem.equipment_id == Equipment.id)
            .where(RequestItem.request_id == request_id)
        )
        items_result = await db.execute(items_query)
        
        # 構建回覆數據
        responses = []
        items_dict = {}
        
        # 獲取所有項目信息
        for item, equipment_name in items_result.all():
            items_dict[item.id] = {
                "itemId": item.id,
                "equipmentName": equipment_name,
                "requestedQuantity": item.requested_quantity,
                "totalAvailableQuantity": 0,
            }
        
        # 處理回覆
        for response, building_name in responses_result.all():
            # 獲取回覆項目
            response_items_query = (
                select(BuildingResponseItem, RequestItem.id.label("request_item_id"), Equipment.name.label("equipment_name"))
                .join(RequestItem, BuildingResponseItem.request_item_id == RequestItem.id)
                .join(Equipment, RequestItem.equipment_id == Equipment.id)
                .where(BuildingResponseItem.response_id == response.id)
            )
            response_items_result = await db.execute(response_items_query)
            
            # 構建項目數據
            response_items = []
            for response_item, request_item_id, equipment_name in response_items_result.all():
                response_items.append({
                    "itemId": request_item_id,
                    "equipmentName": equipment_name,
                    "availableQuantity": response_item.available_quantity,
                })
                
                # 累加可用數量
                if request_item_id in items_dict:
                    items_dict[request_item_id]["totalAvailableQuantity"] += response_item.available_quantity
            
            # 構建回覆數據
            responses.append({
                "responseId": response.id,
                "buildingId": response.building_id,
                "buildingName": building_name,
                "submittedAt": response.submitted_at,
                "items": response_items,
            })
        
        # 構建總可用量數據
        total_available = list(items_dict.values())
        
        return responses, total_available


response = CRUDResponse(BuildingResponse)