import uuid
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import select, update, and_, or_, func, join
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.crud.base import CRUDBase
from app.models.requests import Request, RequestItem, RequestStatusHistory
from app.models.users import User
from app.models.equipment import Equipment
from app.schemas.requests import RequestCreate


class CRUDRequest(CRUDBase[Request, RequestCreate, Any]):
    """申請 CRUD 操作類"""

    async def create_with_items(
        self, db: AsyncSession, *, obj_in: RequestCreate, user_id: str
    ) -> Request:
        """創建新申請及其項目"""
        # 創建申請
        request_id = str(uuid.uuid4())
        db_request = Request(
            id=request_id,
            user_id=user_id,
            start_date=obj_in.startDate,
            end_date=obj_in.endDate,
            venue=obj_in.venue,
            purpose=obj_in.purpose,
            status="pending_review",
        )
        db.add(db_request)
        
        # 創建申請項目
        for item in obj_in.items:
            db_item = RequestItem(
                id=str(uuid.uuid4()),
                request_id=request_id,
                equipment_id=item.equipmentId,
                requested_quantity=item.quantity,
            )
            db.add(db_item)
        
        # 創建狀態歷史
        status_history = RequestStatusHistory(
            id=str(uuid.uuid4()),
            request_id=request_id,
            status="pending_review",
            operator_id=user_id,
            notes="已建立申請",
        )
        db.add(status_history)
        
        await db.commit()
        await db.refresh(db_request)
        return db_request

    async def get_requests(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date_from: Optional[date] = None,
        start_date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 20,
        is_admin: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """獲取申請列表
        
        Args:
            user_id: 申請人ID (非管理員只能查看自己的申請)
            status: 申請狀態
            start_date_from: 開始日期下限
            start_date_to: 開始日期上限
            skip: 跳過記錄數
            limit: 返回記錄數上限
            is_admin: 是否為管理員 (決定是否能查看所有申請)
        """
        # 構建查詢條件
        conditions = []
        if not is_admin and user_id:
            conditions.append(Request.user_id == user_id)
        elif user_id and is_admin:
            conditions.append(Request.user_id == user_id)
        
        if status:
            conditions.append(Request.status == status)
        
        if start_date_from:
            conditions.append(Request.start_date >= start_date_from)
        
        if start_date_to:
            conditions.append(Request.start_date <= start_date_to)
        
        # 計算總數
        count_query = select(func.count()).select_from(Request)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # 獲取數據
        query = (
            select(Request, User.username)
            .join(User, Request.user_id == User.id)
            .order_by(Request.created_at.desc())
        )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        
        # 構建返回數據
        requests = []
        for request, username in result.all():
            requests.append({
                "requestId": request.id,
                "userId": request.user_id,
                "username": username,
                "startDate": request.start_date,
                "endDate": request.end_date,
                "venue": request.venue,
                "status": request.status,
                "createdAt": request.created_at,
            })
        
        return requests, total

    async def get_request_detail(self, db: AsyncSession, *, request_id: str) -> Optional[Dict[str, Any]]:
        """獲取申請詳情"""
        # 獲取申請基本信息
        query = (
            select(Request, User.username)
            .join(User, Request.user_id == User.id)
            .where(Request.id == request_id)
        )
        result = await db.execute(query)
        request_result = result.first()
        
        if not request_result:
            return None
        
        request, username = request_result
        
        # 獲取申請項目
        items_query = (
            select(RequestItem, Equipment.name.label("equipment_name"))
            .join(Equipment, RequestItem.equipment_id == Equipment.id)
            .where(RequestItem.request_id == request_id)
        )
        items_result = await db.execute(items_query)
        
        # 獲取狀態歷史
        history_query = (
            select(RequestStatusHistory, User.username.label("operator_name"))
            .join(User, RequestStatusHistory.operator_id == User.id)
            .where(RequestStatusHistory.request_id == request_id)
            .order_by(RequestStatusHistory.timestamp)
        )
        history_result = await db.execute(history_query)
        
        # 構建返回數據
        items = []
        for item, equipment_name in items_result.all():
            items.append({
                "itemId": item.id,
                "equipmentName": equipment_name,
                "requestedQuantity": item.requested_quantity,
                "approvedQuantity": item.approved_quantity,
                "allocations": []  # 分配詳情需要在實際使用時具體實現
            })
        
        status_history = []
        for history, operator_name in history_result.all():
            status_history.append({
                "status": history.status,
                "timestamp": history.timestamp,
                "operatorId": history.operator_id,
                "operatorName": operator_name,
                "notes": history.notes,
            })
        
        # 構建詳情
        detail = {
            "requestId": request.id,
            "userId": request.user_id,
            "username": username,
            "startDate": request.start_date,
            "endDate": request.end_date,
            "venue": request.venue,
            "purpose": request.purpose,
            "status": request.status,
            "createdAt": request.created_at,
            "items": items,
            "statusHistory": status_history,
        }
        
        return detail

    async def update_status(
        self,
        db: AsyncSession,
        *,
        request_id: str,
        new_status: str,
        operator_id: str,
        notes: Optional[str] = None,
    ) -> Optional[Request]:
        """更新申請狀態"""
        # 獲取申請
        query = select(Request).where(Request.id == request_id)
        result = await db.execute(query)
        request = result.scalars().first()
        
        if not request:
            return None
        
        # 更新狀態
        request.status = new_status
        request.updated_at = datetime.utcnow()
        
        # 添加狀態歷史
        status_history = RequestStatusHistory(
            id=str(uuid.uuid4()),
            request_id=request_id,
            status=new_status,
            operator_id=operator_id,
            notes=notes,
        )
        db.add(status_history)
        
        await db.commit()
        await db.refresh(request)
        return request

    async def close_request(
        self, db: AsyncSession, *, request_id: str, user_id: str
    ) -> Optional[Request]:
        """關閉申請 (僅申請人可操作)"""
        # 獲取申請
        query = select(Request).where(Request.id == request_id)
        result = await db.execute(query)
        request = result.scalars().first()
        
        if not request:
            return None
        
        # 檢查是否為申請人
        if request.user_id != user_id:
            return None
        
        # 檢查狀態是否為待審核
        if request.status != "pending_review":
            return None
        
        # 更新狀態
        return await self.update_status(
            db,
            request_id=request_id,
            new_status="closed",
            operator_id=user_id,
            notes="申請人主動關閉申請",
        )

    async def reject_request(
        self, db: AsyncSession, *, request_id: str, operator_id: str, reason: str
    ) -> Optional[Request]:
        """駁回申請 (教務處人員可操作)"""
        # 獲取申請
        query = select(Request).where(Request.id == request_id)
        result = await db.execute(query)
        request = result.scalars().first()
        
        if not request:
            return None
        
        # 檢查狀態是否為待審核
        if request.status != "pending_review":
            return None
        
        # 更新狀態
        return await self.update_status(
            db,
            request_id=request_id,
            new_status="rejected",
            operator_id=operator_id,
            notes=reason,
        )

    async def approve_inquiry(
        self, db: AsyncSession, *, request_id: str, operator_id: str
    ) -> Optional[Request]:
        """同意詢問 (教務處人員可操作)"""
        # 獲取申請
        query = select(Request).where(Request.id == request_id)
        result = await db.execute(query)
        request = result.scalars().first()
        
        if not request:
            return None
        
        # 檢查狀態是否為待審核
        if request.status != "pending_review":
            return None
        
        # 更新狀態
        return await self.update_status(
            db,
            request_id=request_id,
            new_status="pending_building_response",
            operator_id=operator_id,
            notes="已同意詢問大樓管理員",
        )


request = CRUDRequest(Request)