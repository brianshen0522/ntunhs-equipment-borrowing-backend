import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Equipment(Base):
    """器材模型，對應資料庫 equipment 資料表"""
    __tablename__ = "equipment"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)  # 新增器材描述欄位
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # 關聯
    creator = relationship("User", foreign_keys=[created_by])
    request_items = relationship("RequestItem", back_populates="equipment")

    def __repr__(self) -> str:
        return f"<Equipment {self.name}>"