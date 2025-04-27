from typing import List, Optional

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate


class CRUDEquipment(CRUDBase[Equipment, EquipmentCreate, EquipmentUpdate]):
    """器材 CRUD 操作類"""

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Equipment]:
        """根據名稱獲取器材"""
        query = select(Equipment).where(Equipment.name == name)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_all(
        self, db: AsyncSession, *, include_disabled: bool = False
    ) -> List[Equipment]:
        """獲取所有器材
        
        Args:
            include_disabled: 是否包含停用的器材
        """
        if include_disabled:
            query = select(Equipment).order_by(Equipment.name)
        else:
            query = select(Equipment).where(Equipment.enabled == True).order_by(Equipment.name)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, *, obj_in: EquipmentCreate, created_by: str
    ) -> Equipment:
        """創建新器材"""
        # 檢查名稱是否已存在
        existing = await self.get_by_name(db, name=obj_in.equipmentName)
        if existing:
            return None  # 名稱已存在

        db_obj = Equipment(
            name=obj_in.equipmentName,
            description=obj_in.description,
            enabled=obj_in.enabled if obj_in.enabled is not None else True,
            created_by=created_by,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: Equipment, obj_in: EquipmentUpdate
    ) -> Equipment:
        """更新器材資訊"""
        # 檢查名稱是否已存在
        if obj_in.equipmentName != db_obj.name:
            existing = await self.get_by_name(db, name=obj_in.equipmentName)
            if existing:
                return None  # 名稱已存在

        # 更新欄位
        db_obj.name = obj_in.equipmentName
        db_obj.description = obj_in.description
        if obj_in.enabled is not None:
            db_obj.enabled = obj_in.enabled
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def toggle_status(
        self, db: AsyncSession, *, db_obj: Equipment, enabled: bool
    ) -> Equipment:
        """啟用/停用器材"""
        db_obj.enabled = enabled
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def check_can_delete(self, db: AsyncSession, *, equipment_id: str) -> bool:
        """檢查器材是否可以刪除（沒有相關的未完成申請）"""
        # 此函數需要檢查是否有任何處於活躍狀態的申請關聯到此器材
        # 具體實現會依據相關表結構，這裡為簡化返回 True
        return True

    async def get_related_requests(self, db: AsyncSession, *, equipment_id: str) -> List[str]:
        """獲取相關的申請"""
        # 返回所有與此器材關聯且未完成的申請ID列表
        # 實現時需要查詢 request_items 和相關表
        return []


equipment = CRUDEquipment(Equipment)