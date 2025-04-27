import uuid
from datetime import date, datetime
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Request(Base):
    """借用申請模型，對應資料庫 requests 資料表"""
    __tablename__ = "requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    venue = Column(String(100), nullable=False)
    purpose = Column(Text, nullable=False)
    status = Column(
        String(30),
        nullable=False,
        default="pending_review",
        # 狀態：pending_review, pending_building_response, pending_allocation, completed, rejected, closed
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)
    pdf_path = Column(String(255), nullable=True)
    email_sent = Column(Boolean, nullable=False, default=False)

    # 關聯
    applicant = relationship("User", foreign_keys=[user_id])
    items = relationship("RequestItem", back_populates="request", cascade="all, delete-orphan")
    status_history = relationship("RequestStatusHistory", back_populates="request", cascade="all, delete-orphan")
    response_tokens = relationship("BuildingResponseToken", back_populates="request", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Request {self.id} by {self.user_id}>"


class RequestItem(Base):
    """借用申請項目模型，對應資料庫 request_items 資料表"""
    __tablename__ = "request_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(String(36), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    requested_quantity = Column(Integer, nullable=False)
    approved_quantity = Column(Integer, nullable=True)

    # 關聯
    request = relationship("Request", back_populates="items")
    equipment = relationship("Equipment", back_populates="request_items")
    response_items = relationship("BuildingResponseItem", back_populates="request_item", cascade="all, delete-orphan")
    allocations = relationship("Allocation", back_populates="request_item", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<RequestItem {self.id} for {self.request_id}>"


class RequestStatusHistory(Base):
    """申請狀態歷史模型，對應資料庫 request_status_history 資料表"""
    __tablename__ = "request_status_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    operator_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    notes = Column(Text, nullable=True)

    # 關聯
    request = relationship("Request", back_populates="status_history")
    operator = relationship("User", foreign_keys=[operator_id])

    def __repr__(self) -> str:
        return f"<RequestStatusHistory {self.status} for {self.request_id}>"