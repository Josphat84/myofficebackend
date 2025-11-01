# app/api/maintenance/__init__.py
# This would be the backend API structure

# app/api/maintenance/models.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MaintenanceStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MaintenancePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ChecklistItem(BaseModel):
    task: str
    completed: bool = False

class WorkOrderCreate(BaseModel):
    title: str
    equipment_id: str
    description: str
    priority: MaintenancePriority
    assigned_to: Optional[str] = None
    scheduled_date: datetime
    estimated_hours: float
    checklist: List[ChecklistItem] = []

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[MaintenanceStatus] = None
    priority: Optional[MaintenancePriority] = None
    assigned_to: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    cost: Optional[float] = None
    completed_at: Optional[datetime] = None
    checklist: Optional[List[ChecklistItem]] = None

class WorkOrderResponse(WorkOrderCreate):
    id: str
    status: MaintenanceStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    actual_hours: Optional[float] = None
    cost: Optional[float] = None

# app/api/maintenance/routes.py
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from .models import WorkOrderCreate, WorkOrderUpdate, WorkOrderResponse

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

# Mock database - in real app, this would be your actual database
work_orders_db = {}

@router.get("/work-orders", response_model=List[WorkOrderResponse])
async def get_work_orders(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    equipment_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100
):
    """Get all work orders with filtering and pagination"""
    filtered_orders = list(work_orders_db.values())
    
    # Apply filters
    if status:
        filtered_orders = [wo for wo in filtered_orders if wo.status == status]
    if priority:
        filtered_orders = [wo for wo in filtered_orders if wo.priority == priority]
    if equipment_id:
        filtered_orders = [wo for wo in filtered_orders if wo.equipment_id == equipment_id]
    if search:
        search_lower = search.lower()
        filtered_orders = [
            wo for wo in filtered_orders 
            if search_lower in wo.title.lower() or search_lower in wo.description.lower()
        ]
    
    return filtered_orders[skip:skip + limit]

@router.get("/work-orders/{work_order_id}", response_model=WorkOrderResponse)
async def get_work_order(work_order_id: str):
    """Get a specific work order by ID"""
    if work_order_id not in work_orders_db:
        raise HTTPException(status_code=404, detail="Work order not found")
    return work_orders_db[work_order_id]

@router.post("/work-orders", response_model=WorkOrderResponse)
async def create_work_order(work_order: WorkOrderCreate):
    """Create a new work order"""
    work_order_id = f"wo-{len(work_orders_db) + 1}"
    now = datetime.now()
    
    new_work_order = WorkOrderResponse(
        id=work_order_id,
        **work_order.dict(),
        status="pending",
        created_at=now,
        updated_at=now
    )
    
    work_orders_db[work_order_id] = new_work_order
    return new_work_order

@router.put("/work-orders/{work_order_id}", response_model=WorkOrderResponse)
async def update_work_order(work_order_id: str, updates: WorkOrderUpdate):
    """Update an existing work order"""
    if work_order_id not in work_orders_db:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    existing_order = work_orders_db[work_order_id]
    update_data = updates.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        setattr(existing_order, field, value)
    
    existing_order.updated_at = datetime.now()
    work_orders_db[work_order_id] = existing_order
    
    return existing_order

@router.delete("/work-orders/{work_order_id}")
async def delete_work_order(work_order_id: str):
    """Delete a work order"""
    if work_order_id not in work_orders_db:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    del work_orders_db[work_order_id]
    return {"message": "Work order deleted successfully"}

@router.get("/equipment/{equipment_id}/maintenance-history")
async def get_equipment_maintenance_history(equipment_id: str):
    """Get maintenance history for specific equipment"""
    equipment_orders = [
        wo for wo in work_orders_db.values() 
        if wo.equipment_id == equipment_id
    ]
    return sorted(equipment_orders, key=lambda x: x.created_at, reverse=True)

@router.get("/stats/overview")
async def get_maintenance_stats():
    """Get maintenance statistics for dashboard"""
    total_orders = len(work_orders_db)
    completed_orders = len([wo for wo in work_orders_db.values() if wo.status == "completed"])
    in_progress_orders = len([wo for wo in work_orders_db.values() if wo.status == "in-progress"])
    high_priority_orders = len([wo for wo in work_orders_db.values() if wo.priority in ["high", "critical"]])
    
    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "in_progress_orders": in_progress_orders,
        "high_priority_orders": high_priority_orders,
        "completion_rate": (completed_orders / total_orders * 100) if total_orders > 0 else 0
    }