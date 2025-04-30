import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import select, update, and_, or_, func, join
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.allocations import Allocation
from app.models.requests import Request, RequestItem
from app.models.responses import BuildingResponse, BuildingResponseItem
from app.models.buildings import Building
from app.models.equipment import Equipment
from app.models.users import User
from app.schemas.allocations import AllocationCreate, ItemAllocationBase
from app.crud.responses import response as crud_response


class CRUDAllocation(CRUDBase[Allocation, AllocationCreate, Any]):
    """器材分配 CRUD 操作類"""

    async def allocate_equipment(
        self, db: AsyncSession, *, request_id: str, obj_in: AllocationCreate, operator_id: str
    ) -> Optional[Request]:
        """分配器材"""
        # 檢查申請是否存在且狀態為待分配
        query = select(Request).where(
            and_(Request.id == request_id, Request.status == "pending_allocation")
        )
        result = await db.execute(query)
        request = result.scalars().first()

        if not request:
            return None

        # 獲取申請項目
        items_query = select(RequestItem).where(RequestItem.request_id == request_id)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()

        # 創建項目ID到物件的映射
        items_map = {item.id: item for item in items}

        # 為每個項目進行分配
        for allocation in obj_in.allocations:
            # 檢查項目是否存在
            if allocation.itemId not in items_map:
                continue

            # 更新核准數量
            item = items_map[allocation.itemId]
            item.approved_quantity = allocation.approvedQuantity

            # 刪除現有分配
            allocations_query = select(Allocation).where(Allocation.request_item_id == item.id)
            allocations_result = await db.execute(allocations_query)
            for existing_allocation in allocations_result.scalars().all():
                await db.delete(existing_allocation)

            # 如果核准數量大於0，創建新分配
            if allocation.approvedQuantity > 0:
                for building_allocation in allocation.buildingAllocations:
                    db_allocation = Allocation(
                        id=str(uuid.uuid4()),
                        request_item_id=item.id,
                        building_id=building_allocation.buildingId,
                        allocated_quantity=building_allocation.allocatedQuantity,
                        allocated_by=operator_id,
                    )
                    db.add(db_allocation)

        # 更新申請狀態和備註
        request.status = "completed"
        request.notes = obj_in.notes
        request.updated_at = datetime.utcnow()

        # 添加狀態歷史
        from app.models.requests import RequestStatusHistory
        status_history = RequestStatusHistory(
            id=str(uuid.uuid4()),
            request_id=request_id,
            status="completed",
            operator_id=operator_id,
            notes=obj_in.notes if obj_in.notes else "分配完成",
        )
        db.add(status_history)

        # Mark all building response tokens as finished
        await crud_response.mark_tokens_as_finished(db, request_id=request_id)
        
        await db.commit()
        await db.refresh(request)
        
        # 發送LINE通知給相關大樓管理員 - 新增的部分
        try:
            # 獲取所有分配的大樓
            building_ids = set()
            for allocation in obj_in.allocations:
                if allocation.approvedQuantity > 0:
                    for building_allocation in allocation.buildingAllocations:
                        building_ids.add(building_allocation.buildingId)
            
            # 為每個大樓發送通知
            from app.services.line_bot import line_bot_service
            for building_id in building_ids:
                # 獲取大樓名稱
                building_query = select(Building).where(Building.id == building_id)
                building_result = await db.execute(building_query)
                building = building_result.scalars().first()
                
                if building:
                    # 發送分配完成通知
                    await line_bot_service.send_allocation_complete_notification(
                        db, request_id=request_id, building_name=building.name
                    )
        except Exception as e:
            # 記錄錯誤，但不中斷流程
            await logging_service.error(
                db,
                component="line",
                message=f"發送分配完成通知失敗",
                details=str(e),
                request_id=request_id
            )
        
        return request

    async def generate_pdf(self, db: AsyncSession, *, request_id: str) -> Optional[str]:
        """生成借用單 PDF

        在實際應用中，這裡會使用 PDF 生成庫生成文件，
        此處僅模擬返回檔案路徑
        """
        # 檢查申請是否存在且狀態為已完成
        query = select(Request).where(
            and_(Request.id == request_id, Request.status == "completed")
        )
        result = await db.execute(query)
        request = result.scalars().first()

        if not request:
            return None

        # 模擬 PDF 生成並返回路徑
        pdf_path = f"storage/requests/{request_id}.pdf"

        # 更新 PDF 路徑
        request.pdf_path = pdf_path
        await db.commit()

        return pdf_path

    async def send_email(self, db: AsyncSession, *, request_id: str) -> Optional[str]:
        """發送借用單郵件

        在實際應用中，這裡會使用 SMTP 服務發送郵件，
        此處僅模擬發送過程
        """
        # 檢查申請是否存在且狀態為已完成
        query = (
            select(Request, User.email)
            .join(User, Request.user_id == User.id)
            .where(and_(Request.id == request_id, Request.status == "completed"))
        )
        result = await db.execute(query)
        request_result = result.first()

        if not request_result:
            return None

        request, email = request_result

        # 檢查是否有 PDF 路徑
        if not request.pdf_path:
            # 嘗試生成 PDF
            pdf_path = await self.generate_pdf(db, request_id=request_id)
            if not pdf_path:
                return None

        # 模擬發送郵件
        request.email_sent = True
        await db.commit()

        return email


    async def get_allocation_summary(self, db: AsyncSession, *, request_id: str) -> Optional[Dict[str, Any]]:
        """獲取分配摘要"""
        # 檢查申請是否存在
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

        # 獲取申請項目和分配
        items_query = (
            select(
                RequestItem,
                Equipment.name.label("equipment_name"),
                func.array_agg(Allocation.id).label("allocation_ids"),
                func.array_agg(Allocation.building_id).label("building_ids"),
                func.array_agg(Building.name).label("building_names"),
                func.array_agg(Allocation.allocated_quantity).label("allocated_quantities"),
            )
            .join(Equipment, RequestItem.equipment_id == Equipment.id)
            .outerjoin(Allocation, RequestItem.id == Allocation.request_item_id)
            .outerjoin(Building, Allocation.building_id == Building.id)
            .where(RequestItem.request_id == request_id)
            .group_by(RequestItem.id, Equipment.name)
        )
        items_result = await db.execute(items_query)

        # 構建分配摘要
        items = []
        for item, equipment_name, allocation_ids, building_ids, building_names, allocated_quantities in items_result.all():
            allocations = []

            # 如果有分配數據
            if allocation_ids and allocation_ids[0] is not None:
                for i in range(len(allocation_ids)):
                    allocations.append({
                        "allocationId": allocation_ids[i],
                        "buildingId": building_ids[i],
                        "buildingName": building_names[i],
                        "allocatedQuantity": allocated_quantities[i],
                    })

            items.append({
                "itemId": item.id,
                "equipmentName": equipment_name,
                "requestedQuantity": item.requested_quantity,
                "approvedQuantity": item.approved_quantity,
                "allocations": allocations,
            })

        return {
            "requestId": request.id,
            "status": request.status,
            "userId": request.user_id,
            "username": username,
            "startDate": request.start_date,
            "endDate": request.end_date,
            "venue": request.venue,
            "pdfPath": request.pdf_path,
            "emailSent": request.email_sent,
            "notes": request.notes,
            "items": items,
        }

allocation = CRUDAllocation(Allocation)