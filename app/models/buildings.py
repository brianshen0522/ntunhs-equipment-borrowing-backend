import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base


class Building(Base):
    """大樓模型，對應資料庫 buildings 資料表"""
    __tablename__ = "buildings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # 關聯
    creator = relationship("User", foreign_keys=[created_by])
    responses = relationship("BuildingResponse", back_populates="building")
    allocations = relationship("Allocation", back_populates="building")
    # 移除與設備的關聯 (equipment relationship)，因為設備不再與大樓關聯

    def __repr__(self) -> str:
        return f"<Building {self.name}>"