from typing import List, Optional

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.buildings import Building
from app.schemas.buildings import BuildingCreate, BuildingUpdate


class CRUDBuilding(CRUDBase[Building, BuildingCreate, BuildingUpdate]):
    """大樓 CRUD 操作類"""

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Building]:
        """根據名稱獲取大樓"""
        query = select(Building).where(Building.name == name)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_all(
        self, db: AsyncSession, *, include_disabled: bool = False
    ) -> List[Building]:
        """獲取所有大樓
        
        Args:
            include_disabled: 是否包含停用的大樓
        """
        if include_disabled:
            query = select(Building).order_by(Building.name)
        else:
            query = select(Building).where(Building.enabled == True).order_by(Building.name)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, *, obj_in: BuildingCreate, created_by: str
    ) -> Building:
        """創建新大樓"""
        # 檢查名稱是否已存在
        existing = await self.get_by_name(db, name=obj_in.buildingName)
        if existing:
            return None  # 名稱已存在

        db_obj = Building(
            name=obj_in.buildingName,
            enabled=True,
            created_by=created_by,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_name(
        self, db: AsyncSession, *, db_obj: Building, name: str
    ) -> Building:
        """更新大樓名稱"""
        # 檢查名稱是否已存在
        if name != db_obj.name:
            existing = await self.get_by_name(db, name=name)
            if existing:
                return None  # 名稱已存在

        db_obj.name = name
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def toggle_status(
        self, db: AsyncSession, *, db_obj: Building, enabled: bool
    ) -> Building:
        """啟用/停用大樓"""
        db_obj.enabled = enabled
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def check_can_delete(self, db: AsyncSession, *, building_id: str) -> bool:
        """檢查大樓是否可以刪除（沒有相關的未完成申請）"""
        # 此函數需要檢查是否有任何處於活躍狀態的申請關聯到此大樓
        # 具體實現會依據相關表結構，這裡為簡化返回 True
        return True

    async def get_related_requests(self, db: AsyncSession, *, building_id: str) -> List[str]:
        """獲取相關的申請"""
        # 返回所有與此大樓關聯且未完成的申請ID列表
        # 實現時需要查詢 allocations 和相關表
        return []


building = CRUDBuilding(Building)