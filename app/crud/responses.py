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
            is_finished=False,  # Initialize as not finished
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
                    BuildingResponseToken.is_finished == False,  # Only allow access if not finished
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

        # Allow access if status is pending_building_response OR pending_allocation
        if not request or (request.status != "pending_building_response" and request.status != "pending_allocation"):
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

        # 獲取所有先前回覆（如果有的話）
        building_responses = []
        current_building_response = None  # To store response for the current form session

        if token_obj.is_used:
            # Get all responses for this token
            responses_query = (
                select(BuildingResponse, Building.name.label("building_name"))
                .join(Building, BuildingResponse.building_id == Building.id)
                .where(BuildingResponse.response_token_id == token_obj.id)
            )
            responses_result = await db.execute(responses_query)
            all_responses = responses_result.all()
            
            # Process each building's response
            for response, building_name in all_responses:
                # 獲取回覆項目
                response_items_query = (
                    select(BuildingResponseItem, RequestItem.id.label("request_item_id"), Equipment.name.label("equipment_name"))
                    .join(RequestItem, BuildingResponseItem.request_item_id == RequestItem.id)
                    .join(Equipment, RequestItem.equipment_id == Equipment.id)
                    .where(BuildingResponseItem.response_id == response.id)
                )
                response_items_result = await db.execute(response_items_query)
                
                response_items = []
                for response_item, request_item_id, equipment_name in response_items_result.all():
                    response_items.append({
                        "itemId": request_item_id,
                        "equipmentName": equipment_name,
                        "availableQuantity": response_item.available_quantity,
                    })
                
                building_response = {
                    "buildingId": response.building_id,
                    "buildingName": building_name,
                    "items": response_items,
                    "submittedAt": response.submitted_at
                }
                
                building_responses.append(building_response)
                
                # Check if this response is for the current building in the URL query
                # This is a placeholder for determining which building's response is being edited
                # In a real implementation, you might use URL parameters or session data
                user_agent_ip = None  # This would be set from the request context
                if user_agent_ip and response.ip_address == user_agent_ip:
                    current_building_response = building_response
        
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

        return {
            "requestId": request.id,
            "requestDetails": {
                "startDate": request.start_date,
                "endDate": request.end_date,
                "venue": request.venue,
            },
            "items": items,
            "buildings": buildings,
            "responseData": current_building_response or {},  # Current building's response for form prefill
            "allBuildingResponses": building_responses,  # All building responses for this token
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
                    BuildingResponseToken.is_finished == False,  # Only allow submission if not finished
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

        # Allow submission if status is pending_building_response OR pending_allocation
        if not request or (request.status != "pending_building_response" and request.status != "pending_allocation"):
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

        # 檢查是否為同一大樓的回覆更新（同一個token, 同一個大樓）
        is_update = False
        if token_obj.is_used:
            response_query = (
                select(BuildingResponse)
                .where(
                    and_(
                        BuildingResponse.response_token_id == token_obj.id,
                        BuildingResponse.building_id == obj_in.buildingId
                    )
                )
            )
            response_result = await db.execute(response_query)
            existing_response = response_result.scalars().first()

            if existing_response:
                is_update = True
                # 更新現有回覆
                existing_response.submitted_at = datetime.utcnow()  # Update submission time
                if ip_address:
                    existing_response.ip_address = ip_address

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

                # Add status history entry for this building's updated response
                from app.models.requests import RequestStatusHistory
                status_history = RequestStatusHistory(
                    id=str(uuid.uuid4()),
                    request_id=request.id,
                    status=request.status,  # Keep the current status
                    operator_id=request.user_id,  # Using requester ID as the operator
                    notes=f"{building.name}大樓管理員已更新回覆",
                )
                db.add(status_history)

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
        # Note: We no longer set is_finished here

        # First submission from any building changes the status to pending_allocation if needed
        status_changed = False
        if request.status == "pending_building_response":
            request.status = "pending_allocation"
            request.updated_at = datetime.utcnow()
            status_changed = True

        # Always add a status history entry with the building name
        from app.models.requests import RequestStatusHistory
        
        # If this is a status change, add an entry with the new status
        if status_changed:
            status_history = RequestStatusHistory(
                id=str(uuid.uuid4()),
                request_id=request.id,
                status="pending_allocation",
                operator_id=request.user_id,  # Using requester ID as the operator
                notes=f"{building.name}大樓管理員已提交回覆，申請狀態更新為待分配",
            )
        else:
            # If status isn't changing, still add a history entry with current status
            status_history = RequestStatusHistory(
                id=str(uuid.uuid4()),
                request_id=request.id,
                status=request.status,
                operator_id=request.user_id,  # Using requester ID as the operator
                notes=f"{building.name}大樓管理員已提交回覆",
            )
        
        db.add(status_history)

        await db.commit()
        await db.refresh(db_response)

        return db_response

    async def mark_tokens_as_finished(self, db: AsyncSession, *, request_id: str) -> bool:
        """標記請求的所有令牌為已完成"""
        try:
            # Find all tokens for this request
            tokens_query = select(BuildingResponseToken).where(
                BuildingResponseToken.request_id == request_id
            )
            tokens_result = await db.execute(tokens_query)
            tokens = tokens_result.scalars().all()
            
            # Mark all tokens as finished
            for token in tokens:
                token.is_finished = True
            
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            return False

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