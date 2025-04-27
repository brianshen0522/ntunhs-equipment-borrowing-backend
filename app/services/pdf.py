import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from sqlalchemy import select, join
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import SystemLog
from app.models.requests import Request, RequestItem
from app.models.users import User
from app.models.equipment import Equipment
from app.models.allocations import Allocation
from app.models.buildings import Building

class PdfService:
    """
    PDF 服務
    處理借用單 PDF 生成
    """
    
    @classmethod
    async def generate_borrowing_form(cls, db: AsyncSession, request_id: str) -> Optional[str]:
        """
        生成借用單 PDF
        
        Args:
            db: 資料庫連接
            request_id: 申請ID
            
        Returns:
            Optional[str]: PDF 文件路徑，如果失敗則返回 None
        """
        try:
            # 獲取申請和用戶信息
            query = (
                select(Request, User.username)
                .join(User, Request.user_id == User.id)
                .where(Request.id == request_id)
            )
            result = await db.execute(query)
            request_data = result.first()
            
            if not request_data:
                # 記錄錯誤
                log = SystemLog(
                    level="error",
                    component="pdf",
                    message=f"找不到申請，無法生成借用單 PDF",
                    details=json.dumps({"requestId": request_id}),
                )
                db.add(log)
                await db.commit()
                return None
            
            request, username = request_data
            
            # 獲取申請項目和分配信息
            items_query = (
                select(
                    RequestItem,
                    Equipment.name.label("equipment_name"),
                )
                .join(Equipment, RequestItem.equipment_id == Equipment.id)
                .where(RequestItem.request_id == request_id)
            )
            items_result = await db.execute(items_query)
            items_data = items_result.all()
            
            items = []
            for item, equipment_name in items_data:
                # 獲取該項目的分配
                allocations_query = (
                    select(
                        Allocation,
                        Building.name.label("building_name"),
                    )
                    .join(Building, Allocation.building_id == Building.id)
                    .where(Allocation.request_item_id == item.id)
                )
                allocations_result = await db.execute(allocations_query)
                allocations_data = allocations_result.all()
                
                allocations = []
                for allocation, building_name in allocations_data:
                    allocations.append({
                        "buildingName": building_name,
                        "allocatedQuantity": allocation.allocated_quantity,
                    })
                
                items.append({
                    "equipmentName": equipment_name,
                    "requestedQuantity": item.requested_quantity,
                    "approvedQuantity": item.approved_quantity,
                    "allocations": allocations,
                })
            
            # 準備 PDF 生成所需的數據
            pdf_data = {
                "requestId": request.id,
                "applicant": username,
                "startDate": request.start_date.strftime("%Y-%m-%d"),
                "endDate": request.end_date.strftime("%Y-%m-%d"),
                "venue": request.venue,
                "purpose": request.purpose,
                "items": items,
                "notes": request.notes,
                "generatedAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            # 實際應用中，這裡會使用 PDF 生成庫生成文件
            # 此處簡化為模擬生成
            # from reportlab.lib.pagesizes import letter
            # from reportlab.pdfgen import canvas
            # from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            # from reportlab.lib.styles import getSampleStyleSheet
            
            # 確保目錄存在
            storage_dir = Path("storage/requests")
            os.makedirs(storage_dir, exist_ok=True)
            
            # 生成文件路徑
            pdf_path = f"/storage/requests/{request_id}.pdf"
            
            # 模擬 PDF 生成
            # doc = SimpleDocTemplate(storage_dir / f"{request_id}.pdf", pagesize=letter)
            # ...
            
            # 記錄成功
            log = SystemLog(
                level="info",
                component="pdf",
                message=f"借用單 PDF 生成成功",
                details=json.dumps({
                    "requestId": request_id,
                    "pdfPath": pdf_path,
                }),
            )
            db.add(log)
            
            # 更新 PDF 路徑
            request.pdf_path = pdf_path
            await db.commit()
            
            return pdf_path
        except Exception as e:
            # 記錄錯誤
            log = SystemLog(
                level="error",
                component="pdf",
                message=f"借用單 PDF 生成失敗",
                details=json.dumps({
                    "requestId": request_id,
                    "error": str(e),
                }),
            )
            db.add(log)
            await db.commit()
            
            return None

# 創建服務實例
pdf_service = PdfService()