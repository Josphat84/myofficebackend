# app/routers/maintenance.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

router = APIRouter()

# Self-contained models
class MaintenanceStatus(str):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MaintenancePriority(str):
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
    equipment_name: str
    description: str
    priority: str
    category: str
    location: str
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    scheduled_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    reported_by: Optional[str] = None
    reported_by_name: Optional[str] = None
    notes: Optional[str] = None
    checklist: List[ChecklistItem] = []

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    scheduled_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    cost: Optional[float] = None
    completed_date: Optional[str] = None
    notes: Optional[str] = None
    checklist: Optional[List[ChecklistItem]] = None

class WorkOrderResponse(BaseModel):
    id: str
    title: str
    equipment_id: str
    equipment_name: str
    description: str
    priority: str
    category: str
    location: str
    status: str
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    reported_by: Optional[str]
    reported_by_name: Optional[str]
    scheduled_date: Optional[str]
    completed_date: Optional[str]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    cost: Optional[float]
    notes: Optional[str]
    checklist: List[ChecklistItem]
    created_at: str
    updated_at: str

class MaintenanceAssign(BaseModel):
    assigned_to: str
    assigned_to_name: str

class MaintenanceComplete(BaseModel):
    actual_hours: float
    cost: float
    notes: str

# Mock database
work_orders_db = {}

# Initialize with sample data
def initialize_sample_data():
    if not work_orders_db:
        now = datetime.now()
        sample_orders = [
            {
                "id": "maint-001",
                "title": "CNC Machine Calibration",
                "equipment_id": "eq-001",
                "equipment_name": "CNC Machine #1",
                "description": "Routine calibration and maintenance for CNC machine #1",
                "priority": "medium",
                "category": "equipment",
                "location": "Production Floor A",
                "status": "completed",
                "assigned_to": "emp-2",
                "assigned_to_name": "Sarah Chen",
                "reported_by": "emp-1",
                "reported_by_name": "Mike Johnson",
                "scheduled_date": (now.replace(day=now.day-2)).isoformat(),
                "completed_date": (now.replace(day=now.day-1)).isoformat(),
                "estimated_hours": 4.0,
                "actual_hours": 3.5,
                "cost": 0.0,
                "notes": "Calibration completed successfully. Machine operating within specifications.",
                "checklist": [
                    {"task": "Check calibration settings", "completed": True},
                    {"task": "Test machine operation", "completed": True},
                    {"task": "Update maintenance log", "completed": True}
                ],
                "created_at": (now.replace(day=now.day-5)).isoformat(),
                "updated_at": (now.replace(day=now.day-1)).isoformat()
            },
            {
                "id": "maint-002",
                "title": "Forklift Hydraulic Leak",
                "equipment_id": "eq-002",
                "equipment_name": "Forklift #3",
                "description": "Hydraulic fluid leak detected in forklift #3. Needs immediate attention.",
                "priority": "high",
                "category": "vehicle",
                "location": "Warehouse",
                "status": "in-progress",
                "assigned_to": "emp-3",
                "assigned_to_name": "David Rodriguez",
                "reported_by": "emp-4",
                "reported_by_name": "Emily Watson",
                "scheduled_date": now.isoformat(),
                "completed_date": None,
                "estimated_hours": 6.0,
                "actual_hours": None,
                "cost": None,
                "notes": "Seal replacement required. Parts ordered, ETA 2 days.",
                "checklist": [
                    {"task": "Identify leak source", "completed": True},
                    {"task": "Order replacement parts", "completed": True},
                    {"task": "Replace hydraulic seal", "completed": False},
                    {"task": "Test forklift operation", "completed": False}
                ],
                "created_at": (now.replace(day=now.day-1)).isoformat(),
                "updated_at": now.isoformat()
            },
            {
                "id": "maint-003",
                "title": "Server Room Cooling Issue",
                "equipment_id": "eq-003",
                "equipment_name": "Server Rack A",
                "description": "Temperature rising in server room. AC unit not maintaining set temperature.",
                "priority": "critical",
                "category": "it",
                "location": "Server Room",
                "status": "open",
                "assigned_to": None,
                "assigned_to_name": None,
                "reported_by": "emp-5",
                "reported_by_name": "Alex Kim",
                "scheduled_date": None,
                "completed_date": None,
                "estimated_hours": 3.0,
                "actual_hours": None,
                "cost": None,
                "notes": "Urgent - server temperatures approaching critical levels.",
                "checklist": [
                    {"task": "Check AC unit operation", "completed": False},
                    {"task": "Monitor server temperatures", "completed": False},
                    {"task": "Contact HVAC technician", "completed": False}
                ],
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
        ]
        
        for order in sample_orders:
            work_orders_db[order["id"]] = order

# Initialize sample data on startup
@router.on_event("startup")
async def startup_event():
    initialize_sample_data()

# Routes
@router.get("/", response_model=List[WorkOrderResponse])
async def get_work_orders(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100
):
    """Get all work orders with filtering and pagination"""
    filtered_orders = list(work_orders_db.values())
    
    # Apply filters
    if status:
        filtered_orders = [wo for wo in filtered_orders if wo["status"] == status]
    if priority:
        filtered_orders = [wo for wo in filtered_orders if wo["priority"] == priority]
    if category:
        filtered_orders = [wo for wo in filtered_orders if wo["category"] == category]
    if search:
        search_lower = search.lower()
        filtered_orders = [
            wo for wo in filtered_orders 
            if search_lower in wo["title"].lower() or search_lower in wo["description"].lower()
        ]
    
    return filtered_orders[skip:skip + limit]

@router.get("/{work_order_id}", response_model=WorkOrderResponse)
async def get_work_order(work_order_id: str):
    """Get a specific work order by ID"""
    if work_order_id not in work_orders_db:
        raise HTTPException(status_code=404, detail="Work order not found")
    return work_orders_db[work_order_id]

@router.post("/", response_model=WorkOrderResponse)
async def create_work_order(work_order: WorkOrderCreate):
    """Create a new work order"""
    work_order_id = f"maint-{str(uuid.uuid4())[:8]}"
    now = datetime.now().isoformat()
    
    new_work_order = {
        "id": work_order_id,
        "title": work_order.title,
        "equipment_id": work_order.equipment_id,
        "equipment_name": work_order.equipment_name,
        "description": work_order.description,
        "priority": work_order.priority,
        "category": work_order.category,
        "location": work_order.location,
        "status": "open",
        "assigned_to": work_order.assigned_to,
        "assigned_to_name": work_order.assigned_to_name,
        "reported_by": work_order.reported_by,
        "reported_by_name": work_order.reported_by_name,
        "scheduled_date": work_order.scheduled_date,
        "completed_date": None,
        "estimated_hours": work_order.estimated_hours,
        "actual_hours": None,
        "cost": None,
        "notes": work_order.notes,
        "checklist": work_order.checklist,
        "created_at": now,
        "updated_at": now
    }
    
    work_orders_db[work_order_id] = new_work_order
    return new_work_order

@router.put("/{work_order_id}", response_model=WorkOrderResponse)
async def update_work_order(work_order_id: str, updates: WorkOrderUpdate):
    """Update an existing work order"""
    if work_order_id not in work_orders_db:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    existing_order = work_orders_db[work_order_id]
    update_data = updates.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        if value is not None:
            existing_order[field] = value
    
    existing_order["updated_at"] = datetime.now().isoformat()
    work_orders_db[work_order_id] = existing_order
    
    return existing_order

@router.put("/{work_order_id}/assign", response_model=WorkOrderResponse)
async def assign_work_order(work_order_id: str, assign_data: MaintenanceAssign):
    """Assign a work order to a technician"""
    if work_order_id not in work_orders_db:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    work_orders_db[work_order_id]["assigned_to"] = assign_data.assigned_to
    work_orders_db[work_order_id]["assigned_to_name"] = assign_data.assigned_to_name
    work_orders_db[work_order_id]["status"] = "in-progress"
    work_orders_db[work_order_id]["updated_at"] = datetime.now().isoformat()
    
    return work_orders_db[work_order_id]

@router.put("/{work_order_id}/complete", response_model=WorkOrderResponse)
async def complete_work_order(work_order_id: str, complete_data: MaintenanceComplete):
    """Mark a work order as completed"""
    if work_order_id not in work_orders_db:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    work_orders_db[work_order_id]["status"] = "completed"
    work_orders_db[work_order_id]["completed_date"] = datetime.now().isoformat()
    work_orders_db[work_order_id]["actual_hours"] = complete_data.actual_hours
    work_orders_db[work_order_id]["cost"] = complete_data.cost
    work_orders_db[work_order_id]["notes"] = complete_data.notes
    work_orders_db[work_order_id]["updated_at"] = datetime.now().isoformat()
    
    # Mark all checklist items as completed
    for item in work_orders_db[work_order_id]["checklist"]:
        item["completed"] = True
    
    return work_orders_db[work_order_id]

@router.delete("/{work_order_id}")
async def delete_work_order(work_order_id: str):
    """Delete a work order"""
    if work_order_id not in work_orders_db:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    del work_orders_db[work_order_id]
    return {"message": "Work order deleted successfully"}

@router.get("/equipment/{equipment_id}/history")
async def get_equipment_maintenance_history(equipment_id: str):
    """Get maintenance history for specific equipment"""
    equipment_orders = [
        wo for wo in work_orders_db.values() 
        if wo["equipment_id"] == equipment_id
    ]
    return sorted(equipment_orders, key=lambda x: x["created_at"], reverse=True)

@router.get("/stats/summary")
async def get_maintenance_stats():
    """Get maintenance statistics for dashboard"""
    total_orders = len(work_orders_db)
    completed_orders = len([wo for wo in work_orders_db.values() if wo["status"] == "completed"])
    in_progress_orders = len([wo for wo in work_orders_db.values() if wo["status"] == "in-progress"])
    open_orders = len([wo for wo in work_orders_db.values() if wo["status"] == "open"])
    critical_orders = len([wo for wo in work_orders_db.values() if wo["priority"] == "critical"])
    
    # Calculate overdue orders
    now = datetime.now()
    overdue_orders = len([
        wo for wo in work_orders_db.values() 
        if wo["status"] in ["open", "in-progress"] and 
        wo["scheduled_date"] and 
        datetime.fromisoformat(wo["scheduled_date"]) < now
    ])
    
    return {
        "total": total_orders,
        "open": open_orders,
        "in_progress": in_progress_orders,
        "completed": completed_orders,
        "critical": critical_orders,
        "overdue": overdue_orders,
        "completion_rate": (completed_orders / total_orders * 100) if total_orders > 0 else 0
    }

@router.get("/categories/list")
async def get_maintenance_categories():
    """Get available maintenance categories and types"""
    return {
        "categories": [
            "equipment", "facility", "vehicle", "safety", "it", "preventive"
        ],
        "statuses": [
            "open", "in-progress", "completed", "cancelled", "scheduled"
        ],
        "priorities": [
            "low", "medium", "high", "critical"
        ]
    }

@router.get("/equipment/list")
async def get_equipment_list():
    """Get available equipment for maintenance"""
    equipment_list = [
        {"id": "eq-001", "name": "CNC Machine #1", "category": "equipment", "location": "Production Floor A"},
        {"id": "eq-002", "name": "Forklift #3", "category": "vehicle", "location": "Warehouse"},
        {"id": "eq-003", "name": "Server Rack A", "category": "it", "location": "Server Room"},
        {"id": "eq-004", "name": "HVAC Unit North", "category": "facility", "location": "Roof"},
        {"id": "eq-005", "name": "Safety Shower", "category": "safety", "location": "Lab Area"}
    ]
    return equipment_list