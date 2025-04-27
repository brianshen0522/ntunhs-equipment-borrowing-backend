import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """使用者模型，對應資料庫 users 資料表"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), nullable=False, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # 關聯 - 明確指定外鍵
    roles = relationship("UserRole", back_populates="user", foreign_keys="UserRole.user_id", cascade="all, delete-orphan")
    # 被指派的角色關係
    assigned_roles = relationship("UserRole", foreign_keys="UserRole.assigned_by")

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class UserRole(Base):
    """使用者角色模型，對應資料庫 user_roles 資料表"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # applicant, academic_staff, system_admin
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    assigned_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # 關聯 - 明確指定外鍵
    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    assigner = relationship("User", foreign_keys=[assigned_by])

    # 設定唯一約束
    __table_args__ = (
        UniqueConstraint('user_id', 'role', name='uq_user_role'),
    )

    def __repr__(self) -> str:
        return f"<UserRole {self.role} for {self.user_id}>"