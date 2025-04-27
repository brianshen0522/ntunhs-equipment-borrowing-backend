import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Allocation(Base):
    """器材分配模型，對應資料庫 allocations 資料表"""
    __tablename__ = "allocations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_item_id = Column(String(36), ForeignKey("request_items.id", ondelete="CASCADE"), nullable=False)
    building_id = Column(String(36), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    allocated_quantity = Column(Integer, nullable=False)
    allocated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    allocated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 關聯
    request_item = relationship("RequestItem", back_populates="allocations")
    building = relationship("Building", back_populates="allocations")
    allocator = relationship("User", foreign_keys=[allocated_by])

    def __repr__(self) -> str:
        return f"<Allocation {self.id} for {self.request_item_id}>"