import uuid
from datetime import datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.config import settings
from app.database import Base


class BuildingResponseToken(Base):
    """大樓回覆令牌模型，對應資料庫 building_response_tokens 資料表"""
    __tablename__ = "building_response_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(hours=settings.RESPONSE_FORM_VALIDITY_HOURS),
    )
    is_used = Column(Boolean, nullable=False, default=False)

    # 關聯
    request = relationship("Request", back_populates="response_tokens")
    responses = relationship("BuildingResponse", back_populates="response_token")

    def __repr__(self) -> str:
        return f"<BuildingResponseToken {self.token[:8]}... for {self.request_id}>"


class BuildingResponse(Base):
    """大樓回覆模型，對應資料庫 building_responses 資料表"""
    __tablename__ = "building_responses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    building_id = Column(String(36), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    response_token_id = Column(
        String(36), ForeignKey("building_response_tokens.id", ondelete="CASCADE"), nullable=False
    )
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)

    # 關聯
    request = relationship("Request")
    building = relationship("Building", back_populates="responses")
    response_token = relationship("BuildingResponseToken", back_populates="responses")
    items = relationship("BuildingResponseItem", back_populates="response", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<BuildingResponse {self.id} from {self.building_id} for {self.request_id}>"


class BuildingResponseItem(Base):
    """大樓回覆項目模型，對應資料庫 building_response_items 資料表"""
    __tablename__ = "building_response_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    response_id = Column(String(36), ForeignKey("building_responses.id", ondelete="CASCADE"), nullable=False)
    request_item_id = Column(String(36), ForeignKey("request_items.id", ondelete="CASCADE"), nullable=False)
    available_quantity = Column(Integer, nullable=False)

    # 關聯
    response = relationship("BuildingResponse", back_populates="items")
    request_item = relationship("RequestItem", back_populates="response_items")

    def __repr__(self) -> str:
        return f"<BuildingResponseItem {self.id} for {self.response_id}>"