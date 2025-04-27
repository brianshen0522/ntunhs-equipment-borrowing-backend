import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import settings
from app.database import init_db

# 設置日誌
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用程式
app = FastAPI(
    title=settings.APP_NAME,
    description="NTUNHS 教務處器材借用管理系統 API",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# 設置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 異常處理中間件
@app.middleware("http")
async def exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "服務器內部錯誤",
                }
            }
        )

# 健康檢查路由
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

# 註冊路由
app.include_router(api_router, prefix=settings.API_PREFIX)

# 啟動事件：初始化資料庫
@app.on_event("startup")
async def startup_db_client():
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        # 在實際生產環境中，這裡可能需要重試或退出應用程式

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting application on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=int(settings.PORT),
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )