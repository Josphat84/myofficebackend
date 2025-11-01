# backend/app/routers/standby.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/standby", tags=["standby"])

# Pydantic models
class StandbySchedule(BaseModel):
    id: str
    employeeId: str
    employeeName: str
    department: str
    date: str
    startTime: str
    endTime: str
    duration: float
    reason: str
    status: str  # scheduled, in-progress, completed, cancelled
    createdAt: str
    updatedAt: str

class StandbyScheduleCreate(BaseModel):
    employeeId: str
    employeeName: str
    department: str
    date: str
    startTime: str
    endTime: str
    reason: str

class StandbyScheduleUpdate(BaseModel):
    employeeId: Optional[str] = None
    employeeName: Optional[str] = None
    department: Optional[str] = None
    date: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None

# Mock database
standby_db = {}

def calculate_duration(start_time: str, end_time: str) -> float:
    """Calculate duration in hours between two time strings"""
    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")
    duration = (end - start).seconds / 3600
    return round(duration, 2)

# Initialize with sample data
def init_sample_data():
    now = datetime.now()
    
    sample_schedules = [
        {
            "id": "std-001",
            "employeeId": "emp-001",
            "employeeName": "John Smith",
            "department": "Maintenance",
            "date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
            "startTime": "18:00",
            "endTime": "06:00",
            "duration": 12.0,
            "reason": "Emergency equipment monitoring",
            "status": "scheduled",
            "createdAt": (now - timedelta(days=2)).isoformat(),
            "updatedAt": (now - timedelta(days=1)).isoformat()
        },
        {
            "id": "std-002",
            "employeeId": "emp-002",
            "employeeName": "Sarah Johnson",
            "department": "Operations",
            "date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
            "startTime": "20:00",
            "endTime": "08:00",
            "duration": 12.0,
            "reason": "Production line support",
            "status": "scheduled",
            "createdAt": (now - timedelta(days=3)).isoformat(),
            "updatedAt": (now - timedelta(days=2)).isoformat()
        },
        {
            "id": "std-003",
            "employeeId": "emp-003",
            "employeeName": "Mike Chen",
            "department": "IT",
            "date": now.strftime("%Y-%m-%d"),
            "startTime": "22:00",
            "endTime": "06:00",
            "duration": 8.0,
            "reason": "System maintenance window",
            "status": "in-progress",
            "createdAt": (now - timedelta(days=5)).isoformat(),
            "updatedAt": (now - timedelta(hours=2)).isoformat()
        },
        {
            "id": "std-004",
            "employeeId": "emp-004",
            "employeeName": "Lisa Rodriguez",
            "department": "Quality Control",
            "date": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
            "startTime": "16:00",
            "endTime": "00:00",
            "duration": 8.0,
            "reason": "Quality audit preparation",
            "status": "completed",
            "createdAt": (now - timedelta(days=7)).isoformat(),
            "updatedAt": (now - timedelta(days=1)).isoformat()
        },
        {
            "id": "std-005",
            "employeeId": "emp-005",
            "employeeName": "David Brown",
            "department": "Security",
            "date": (now + timedelta(days=3)).strftime("%Y-%m-%d"),
            "startTime": "00:00",
            "endTime": "08:00",
            "duration": 8.0,
            "reason": "Facility security monitoring",
            "status": "scheduled",
            "createdAt": (now - timedelta(days=1)).isoformat(),
            "updatedAt": (now - timedelta(days=1)).isoformat()
        }
    ]
    
    for schedule in sample_schedules:
        standby_db[schedule["id"]] = schedule

# Initialize sample data
init_sample_data()

@router.get("/schedules", response_model=List[StandbySchedule])
async def get_standby_schedules(
    department: Optional[str] = None,
    status: Optional[str] = None,
    date: Optional[str] = None,
    employee_id: Optional[str] = None
):
    """Get all standby schedules with optional filtering"""
    schedules = list(standby_db.values())
    
    # Apply filters
    if department:
        schedules = [s for s in schedules if s["department"] == department]
    if status:
        schedules = [s for s in schedules if s["status"] == status]
    if date:
        schedules = [s for s in schedules if s["date"] == date]
    if employee_id:
        schedules = [s for s in schedules if s["employeeId"] == employee_id]
    
    return schedules

@router.get("/schedules/{schedule_id}", response_model=StandbySchedule)
async def get_standby_schedule(schedule_id: str):
    """Get a specific standby schedule by ID"""
    if schedule_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby schedule not found")
    return standby_db[schedule_id]

@router.post("/schedules", response_model=StandbySchedule)
async def create_standby_schedule(schedule: StandbyScheduleCreate):
    """Create a new standby schedule"""
    schedule_id = f"std-{len(standby_db) + 1:03d}"
    now = datetime.now().isoformat()
    
    duration = calculate_duration(schedule.startTime, schedule.endTime)
    
    new_schedule = StandbySchedule(
        id=schedule_id,
        employeeId=schedule.employeeId,
        employeeName=schedule.employeeName,
        department=schedule.department,
        date=schedule.date,
        startTime=schedule.startTime,
        endTime=schedule.endTime,
        duration=duration,
        reason=schedule.reason,
        status="scheduled",
        createdAt=now,
        updatedAt=now
    )
    
    standby_db[schedule_id] = new_schedule.dict()
    return new_schedule

@router.put("/schedules/{schedule_id}", response_model=StandbySchedule)
async def update_standby_schedule(schedule_id: str, schedule_update: StandbyScheduleUpdate):
    """Update an existing standby schedule"""
    if schedule_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby schedule not found")
    
    existing_schedule = standby_db[schedule_id]
    update_data = schedule_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        if value is not None:
            existing_schedule[field] = value
    
    # Recalculate duration if times changed
    if 'startTime' in update_data or 'endTime' in update_data:
        existing_schedule['duration'] = calculate_duration(
            existing_schedule['startTime'],
            existing_schedule['endTime']
        )
    
    existing_schedule['updatedAt'] = datetime.now().isoformat()
    standby_db[schedule_id] = existing_schedule
    
    return existing_schedule

@router.delete("/schedules/{schedule_id}")
async def delete_standby_schedule(schedule_id: str):
    """Delete a standby schedule"""
    if schedule_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby schedule not found")
    
    del standby_db[schedule_id]
    return {"message": "Standby schedule deleted successfully"}

@router.post("/schedules/{schedule_id}/start")
async def start_standby(schedule_id: str):
    """Mark standby schedule as in-progress"""
    if schedule_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby schedule not found")
    
    schedule = standby_db[schedule_id]
    schedule['status'] = 'in-progress'
    schedule['updatedAt'] = datetime.now().isoformat()
    
    standby_db[schedule_id] = schedule
    return {"message": "Standby schedule started", "schedule": schedule}

@router.post("/schedules/{schedule_id}/complete")
async def complete_standby(schedule_id: str):
    """Mark standby schedule as completed"""
    if schedule_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby schedule not found")
    
    schedule = standby_db[schedule_id]
    schedule['status'] = 'completed'
    schedule['updatedAt'] = datetime.now().isoformat()
    
    standby_db[schedule_id] = schedule
    return {"message": "Standby schedule completed", "schedule": schedule}

@router.post("/schedules/{schedule_id}/cancel")
async def cancel_standby(schedule_id: str):
    """Cancel a standby schedule"""
    if schedule_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby schedule not found")
    
    schedule = standby_db[schedule_id]
    schedule['status'] = 'cancelled'
    schedule['updatedAt'] = datetime.now().isoformat()
    
    standby_db[schedule_id] = schedule
    return {"message": "Standby schedule cancelled", "schedule": schedule}

@router.get("/upcoming")
async def get_upcoming_standby():
    """Get upcoming standby schedules (next 7 days)"""
    schedules = list(standby_db.values())
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    upcoming = [
        s for s in schedules 
        if s['date'] >= today and s['date'] <= next_week and s['status'] in ['scheduled', 'in-progress']
    ]
    
    return {
        "count": len(upcoming),
        "schedules": sorted(upcoming, key=lambda x: x['date'])
    }

@router.get("/stats")
async def get_standby_stats():
    """Get standby statistics for dashboard"""
    schedules = list(standby_db.values())
    
    total_schedules = len(schedules)
    scheduled = len([s for s in schedules if s['status'] == 'scheduled'])
    in_progress = len([s for s in schedules if s['status'] == 'in-progress'])
    completed = len([s for s in schedules if s['status'] == 'completed'])
    cancelled = len([s for s in schedules if s['status'] == 'cancelled'])
    
    # Calculate total standby hours
    total_hours = sum(s['duration'] for s in schedules if s['status'] in ['completed', 'in-progress'])
    
    # Calculate department distribution
    departments = {}
    for schedule in schedules:
        dept = schedule['department']
        if dept not in departments:
            departments[dept] = 0
        departments[dept] += 1
    
    return {
        "totalSchedules": total_schedules,
        "scheduled": scheduled,
        "inProgress": in_progress,
        "completed": completed,
        "cancelled": cancelled,
        "totalHours": round(total_hours, 2),
        "departmentDistribution": departments
    }

@router.get("/employees/{employee_id}/schedules")
async def get_employee_standby_schedules(employee_id: str):
    """Get all standby schedules for a specific employee"""
    schedules = [s for s in standby_db.values() if s['employeeId'] == employee_id]
    return {
        "employeeId": employee_id,
        "employeeName": schedules[0]['employeeName'] if schedules else "Unknown",
        "count": len(schedules),
        "schedules": sorted(schedules, key=lambda x: x['date'], reverse=True)
    }

@router.get("/departments")
async def get_departments():
    """Get all departments with standby schedules"""
    departments = set(s['department'] for s in standby_db.values())
    return {"departments": sorted(list(departments))}