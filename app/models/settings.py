import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class LineBotSettings(Base):
    """LINE Bot設定模型，對應資料庫 line_bot_settings 資料表"""
    __tablename__ = "line_bot_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    webhook_url = Column(String(255), nullable=False)
    channel_access_token = Column(String(255), nullable=False)
    channel_secret = Column(String(255), nullable=False)
    building_request_template = Column(Text, nullable=False)
    allocation_complete_template = Column(Text, nullable=False)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # 關聯
    updater = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<LineBotSettings {self.id}>"


class SmtpSettings(Base):
    """SMTP設定模型，對應資料庫 smtp_settings 資料表"""
    __tablename__ = "smtp_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)
    secure = Column(Boolean, nullable=False, default=True)
    username = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)
    sender_email = Column(String(100), nullable=False)
    sender_name = Column(String(50), nullable=False)
    email_templates = Column(Text, nullable=False)  # JSON格式
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # 關聯
    updater = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<SmtpSettings {self.id}>"


class SystemParameters(Base):
    """系統參數模型，對應資料庫 system_parameters 資料表"""
    __tablename__ = "system_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_expiry_days = Column(Integer, nullable=False, default=30)
    response_form_validity_hours = Column(Integer, nullable=False, default=48)
    max_items_per_request = Column(Integer, nullable=False, default=10)
    enable_email_notifications = Column(Boolean, nullable=False, default=True)
    enable_line_notifications = Column(Boolean, nullable=False, default=True)
    system_maintenance_mode = Column(Boolean, nullable=False, default=False)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # 關聯
    updater = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<SystemParameters {self.id}>"


class SystemLog(Base):
    """系統日誌模型，對應資料庫 system_logs 資料表"""
    __tablename__ = "system_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    level = Column(String(10), nullable=False, index=True)  # info, warning, error
    component = Column(String(20), nullable=False, index=True)  # auth, request, email, line
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON格式
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    request_id = Column(String(36), ForeignKey("requests.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)

    # 關聯
    user = relationship("User", foreign_keys=[user_id])
    request = relationship("Request", foreign_keys=[request_id])

    def __repr__(self) -> str:
        return f"<SystemLog {self.id} {self.level}>"