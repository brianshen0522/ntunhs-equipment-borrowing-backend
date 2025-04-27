from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

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