from typing import AsyncGenerator
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text, select

from app.config import settings

# 創建異步引擎
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    future=True,
)

# 創建異步會話
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)

# 宣告基礎模型
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    依賴函數，用於FastAPI端點獲取異步資料庫會話
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 初始化資料庫
async def init_db() -> None:
    """
    初始化資料庫，在應用啟動時使用
    """
    async with engine.begin() as conn:
        # 在需要清除現有表格時使用
        # await conn.run_sync(Base.metadata.drop_all)

        # 創建表格
        await conn.run_sync(Base.metadata.create_all)
    
    # Insert default settings if tables are empty
    await _insert_default_settings()


async def _insert_default_settings():
    """Insert default settings into empty tables"""
    async with async_session() as session:
        # First check for admin user and create if it doesn't exist
        admin_id = await _ensure_admin_user(session)
        
        # Check and insert LINE Bot settings
        line_bot_count = await _count_records(session, "line_bot_settings")
        if line_bot_count == 0:
            query = """
            INSERT INTO line_bot_settings (
                webhook_url, 
                channel_access_token, 
                channel_secret, 
                building_request_template, 
                allocation_complete_template, 
                updated_at, 
                updated_by
            ) VALUES (
                :webhook_url, 
                :channel_access_token, 
                :channel_secret, 
                :building_request_template, 
                :allocation_complete_template, 
                CURRENT_TIMESTAMP, 
                :updated_by
            )
            """
            await session.execute(
                text(query), 
                {
                    "webhook_url": "https://example.com/webhook/line",
                    "channel_access_token": "dummy_channel_access_token_replace_with_real_token_in_production",
                    "channel_secret": "dummy_channel_secret_replace_with_real_secret_in_production",
                    "building_request_template": "您好，NTUNHS設備借用系統有新的借用申請需要回應。請點擊以下連結填寫可提供的器材數量：{{formUrl}}",
                    "allocation_complete_template": "{{buildingName}}大樓管理員，NTUNHS設備借用系統已完成器材分配，請協助準備借用申請{{requestId}}的器材。",
                    "updated_by": admin_id
                }
            )
        
        # Check and insert SMTP settings
        smtp_count = await _count_records(session, "smtp_settings")
        if smtp_count == 0:
            query = """
            INSERT INTO smtp_settings (
                host, 
                port, 
                secure, 
                username, 
                password, 
                sender_email, 
                sender_name, 
                email_templates, 
                updated_at, 
                updated_by
            ) VALUES (
                :host, 
                :port, 
                :secure, 
                :username, 
                :password, 
                :sender_email, 
                :sender_name, 
                :email_templates, 
                CURRENT_TIMESTAMP, 
                :updated_by
            )
            """
            await session.execute(
                text(query), 
                {
                    "host": "smtp.example.com",
                    "port": 587,
                    "secure": True,
                    "username": "notifications@example.com",
                    "password": "dummy_password_replace_with_real_password_in_production",
                    "sender_email": "equipment@ntunhs.edu.tw",
                    "sender_name": "NTUNHS設備借用系統",
                    "email_templates": '{"approvalNotification": {"subject": "您的設備借用申請 {{requestId}} 已核准", "body": "親愛的 {{username}} 您好，\\n\\n您的設備借用申請已核准，請查看附件的借用單。\\n\\n借用單號：{{requestId}}\\n\\n如有任何問題，請聯繫教務處。\\n\\n此致，\\nNTUNHS設備借用系統"}}',
                    "updated_by": admin_id
                }
            )
        
        # Check and insert System parameters
        system_params_count = await _count_records(session, "system_parameters")
        if system_params_count == 0:
            query = """
            INSERT INTO system_parameters (
                request_expiry_days, 
                response_form_validity_hours, 
                max_items_per_request, 
                enable_email_notifications, 
                enable_line_notifications, 
                system_maintenance_mode, 
                updated_at, 
                updated_by
            ) VALUES (
                :request_expiry_days, 
                :response_form_validity_hours, 
                :max_items_per_request, 
                :enable_email_notifications, 
                :enable_line_notifications, 
                :system_maintenance_mode, 
                CURRENT_TIMESTAMP, 
                :updated_by
            )
            """
            await session.execute(
                text(query), 
                {
                    "request_expiry_days": 30,
                    "response_form_validity_hours": 48,
                    "max_items_per_request": 10,
                    "enable_email_notifications": True,
                    "enable_line_notifications": True,
                    "system_maintenance_mode": False,
                    "updated_by": admin_id
                }
            )
        
        await session.commit()


async def _count_records(session, table_name):
    """Count records in a table"""
    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    return result.scalar()


async def _ensure_admin_user(session):
    """
    Ensure that default admin user exists
    Returns the admin user ID
    """
    # Check if admin user exists
    admin_id = "admin001"
    result = await session.execute(text("SELECT COUNT(*) FROM users WHERE id = :id"), {"id": admin_id})
    if result.scalar() == 0:
        # Create admin user
        admin_user_query = """
        INSERT INTO users (
            id, 
            username, 
            email, 
            created_at
        ) VALUES (
            :id, 
            :username, 
            :email, 
            CURRENT_TIMESTAMP
        )
        """
        await session.execute(
            text(admin_user_query), 
            {
                "id": admin_id,
                "username": "系統管理員",
                "email": "admin@example.com"
            }
        )
        
        # Add system_admin role to the user
        admin_role_query = """
        INSERT INTO user_roles (
            user_id, 
            role, 
            assigned_at
        ) VALUES (
            :user_id, 
            :role, 
            CURRENT_TIMESTAMP
        )
        """
        await session.execute(
            text(admin_role_query), 
            {
                "user_id": admin_id, 
                "role": "system_admin"
            }
        )
        
        # Also add applicant role - commonly needed
        applicant_role_query = """
        INSERT INTO user_roles (
            user_id, 
            role, 
            assigned_at
        ) VALUES (
            :user_id, 
            :role, 
            CURRENT_TIMESTAMP
        )
        """
        await session.execute(
            text(applicant_role_query), 
            {
                "user_id": admin_id, 
                "role": "applicant"
            }
        )
        
        # Add academic_staff role too for convenience
        staff_role_query = """
        INSERT INTO user_roles (
            user_id, 
            role, 
            assigned_at
        ) VALUES (
            :user_id, 
            :role, 
            CURRENT_TIMESTAMP
        )
        """
        await session.execute(
            text(staff_role_query), 
            {
                "user_id": admin_id, 
                "role": "academic_staff"
            }
        )
    
    return admin_id