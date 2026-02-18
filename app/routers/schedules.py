from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from app.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/schedules", tags=["Schedules"])

# ========== Pydantic Models ==========
class ScheduleBase(BaseModel):
    title: str
    category: str
    type: str
    description: Optional[str] = None
    location: str
    frequency: str
    next_due: date
    last_completed: Optional[date] = None
    estimated_hours: Optional[float] = None
    priority: str
    status: str
    assigned_to_id: Optional[str] = None
    department: Optional[str] = None
    notes: Optional[str] = None
    equipment_id: Optional[int] = None
    parts_required: Optional[str] = None
    work_order_number: Optional[str] = None
    regulation: Optional[str] = None
    jurisdiction: Optional[str] = None
    responsible_officer: Optional[str] = None
    findings: Optional[str] = None

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    frequency: Optional[str] = None
    next_due: Optional[date] = None
    last_completed: Optional[date] = None
    estimated_hours: Optional[float] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to_id: Optional[str] = None
    department: Optional[str] = None
    notes: Optional[str] = None
    equipment_id: Optional[int] = None
    parts_required: Optional[str] = None
    work_order_number: Optional[str] = None
    regulation: Optional[str] = None
    jurisdiction: Optional[str] = None
    responsible_officer: Optional[str] = None
    findings: Optional[str] = None

class ScheduleResponse(ScheduleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class BulkStatusUpdate(BaseModel):
    ids: List[int]
    status: str
    notes: Optional[str] = None

# ========== Helper Functions ==========
def convert_dates_to_iso(record: dict) -> dict:
    for key, value in record.items():
        if isinstance(value, (date, datetime)):
            record[key] = value.isoformat()
    return record

# ========== Endpoints ==========
@router.get("/employees")
async def get_employees():
    """Get all employees for dropdown"""
    try:
        response = supabase.table("employees").select("employee_id, name, department, position").execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch employees")

@router.get("/equipment")
async def get_equipment():
    """Get all equipment for dropdown"""
    try:
        response = supabase.table("equipment").select("id, name, code, department, location").execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error fetching equipment: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch equipment")

@router.get("", response_model=List[ScheduleResponse])
async def get_schedules(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    department: Optional[str] = Query(None, description="Filter by department"),
    location: Optional[str] = Query(None, description="Filter by location"),
    date_from: Optional[date] = Query(None, description="Start date for next_due"),
    date_to: Optional[date] = Query(None, description="End date for next_due"),
    search: Optional[str] = Query(None, description="Search in title, description, notes"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        query = supabase.table("schedules").select("*")
        if category and category != 'all':
            query = query.eq("category", category)
        if status and status != 'all':
            query = query.eq("status", status)
        if priority and priority != 'all':
            query = query.eq("priority", priority)
        if department and department != 'all':
            query = query.eq("department", department)
        if location and location != 'all':
            query = query.eq("location", location)
        if date_from:
            query = query.gte("next_due", date_from.isoformat())
        if date_to:
            query = query.lte("next_due", date_to.isoformat())
        if search:
            query = query.or_(
                f"title.ilike.%{search}%,description.ilike.%{search}%,notes.ilike.%{search}%"
            )
        response = query.order("next_due").range(offset, offset + limit - 1).execute()
        records = response.data or []
        for r in records:
            convert_dates_to_iso(r)
        return records
    except Exception as e:
        logger.error(f"Error fetching schedules: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch schedules")

@router.post("", response_model=ScheduleResponse)
async def create_schedule(schedule: ScheduleCreate):
    try:
        data = schedule.dict()
        for field in ['next_due', 'last_completed']:
            if data.get(field):
                data[field] = data[field].isoformat()
        data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = data['created_at']
        response = supabase.table("schedules").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Insert failed")
        result = response.data[0]
        convert_dates_to_iso(result)
        return result
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create schedule")

@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int):
    try:
        response = supabase.table("schedules").select("*").eq("id", schedule_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Schedule not found")
        result = response.data[0]
        convert_dates_to_iso(result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch schedule")

@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, update: ScheduleUpdate):
    try:
        existing = supabase.table("schedules").select("*").eq("id", schedule_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Schedule not found")
        data = {k: v for k, v in update.dict().items() if v is not None}
        if data.get('next_due'):
            data['next_due'] = data['next_due'].isoformat()
        if data.get('last_completed'):
            data['last_completed'] = data['last_completed'].isoformat()
        data['updated_at'] = datetime.utcnow().isoformat()
        response = supabase.table("schedules").update(data).eq("id", schedule_id).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Update failed")
        result = response.data[0]
        convert_dates_to_iso(result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to update schedule")

@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    try:
        existing = supabase.table("schedules").select("*").eq("id", schedule_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Schedule not found")
        supabase.table("schedules").delete().eq("id", schedule_id).execute()
        return {"success": True, "message": "Schedule deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete schedule")

@router.post("/bulk/status-update")
async def bulk_status_update(payload: BulkStatusUpdate):
    try:
        if not payload.ids:
            raise HTTPException(status_code=400, detail="No IDs provided")
        valid_statuses = ['open', 'in_progress', 'completed', 'overdue', 'cancelled']
        if payload.status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid status")
        data = {
            "status": payload.status,
            "updated_at": datetime.utcnow().isoformat()
        }
        if payload.notes:
            data["notes"] = payload.notes
        updated = []
        for sid in payload.ids:
            resp = supabase.table("schedules").update(data).eq("id", sid).execute()
            if resp.data:
                updated.append(resp.data[0])
        return {"success": True, "updated_count": len(updated)}
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail="Bulk update failed")

@router.get("/stats/summary")
async def get_stats():
    try:
        response = supabase.table("schedules").select("*").execute()
        schedules = response.data or []
        total = len(schedules)
        today = datetime.utcnow().date()
        overdue = 0
        in_progress = 0
        completed = 0
        compliance_tasks = 0
        compliance_completed = 0
        maintenance_backlog = 0

        for s in schedules:
            status = s.get('status')
            if status == 'in_progress':
                in_progress += 1
            elif status == 'completed':
                completed += 1
            if s.get('category') == 'compliance':
                compliance_tasks += 1
                if status == 'completed':
                    compliance_completed += 1
            elif s.get('category') == 'maintenance' and status not in ['completed', 'cancelled']:
                maintenance_backlog += 1
            # Overdue check
            due = s.get('next_due')
            if due and status not in ['completed', 'cancelled']:
                try:
                    due_date = datetime.strptime(due, '%Y-%m-%d').date() if isinstance(due, str) else due
                    if due_date < today:
                        overdue += 1
                except:
                    pass

        compliance_rate = (compliance_completed / compliance_tasks * 100) if compliance_tasks else 0
        return {
            "total": total,
            "overdue": overdue,
            "inProgress": in_progress,
            "completed": completed,
            "complianceRate": round(compliance_rate, 2),
            "maintenanceBacklog": maintenance_backlog
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")

@router.get("/departments/list")
async def get_departments():
    """Get unique departments from schedules and employees (combined)"""
    try:
        depts = set()
        # From schedules
        sched_resp = supabase.table("schedules").select("department").execute()
        if sched_resp.data:
            depts.update(d['department'] for d in sched_resp.data if d.get('department'))
        # From employees (active)
        emp_resp = supabase.table("employees").select("department").eq("status", "active").execute()
        if emp_resp.data:
            depts.update(d['department'] for d in emp_resp.data if d.get('department'))
        return sorted(depts)
    except Exception as e:
        logger.error(f"Error fetching departments: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch departments")

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "schedules"}