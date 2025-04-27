from fastapi import APIRouter

from app.api import auth, buildings, equipment, requests, responses, allocations, admin_users, admin_settings

api_router = APIRouter()

# 註冊各模組的路由
api_router.include_router(auth.router)
api_router.include_router(buildings.router)
api_router.include_router(equipment.router)  # 使用 /equipments 端點
api_router.include_router(requests.router)
api_router.include_router(responses.router)
api_router.include_router(allocations.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_settings.router)