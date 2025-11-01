# backend/app/routers/overtime.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum

router = APIRouter(prefix="/api/overtime", tags=["overtime"])

# Pydantic models
class OvertimeStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"

class OvertimeRequest(BaseModel):
    id: str
    employeeId: str
    employeeName: str
    department: str
    date: str
    startTime: str
    endTime: str
    totalHours: float
    reason: str
    status: OvertimeStatus
    rate: float
    totalAmount: float
    approvedBy: Optional[str] = None
    approvedAt: Optional[str] = None
    createdAt: str
    updatedAt: str

class OvertimeRequestCreate(BaseModel):
    employeeId: str
    date: str
    startTime: str
    endTime: str
    reason: str

class OvertimeRequestUpdate(BaseModel):
    date: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[OvertimeStatus] = None
    approvedBy: Optional[str] = None

# Mock database
overtime_db = {}

def calculate_overtime_hours(start_time: str, end_time: str) -> float:
    """Calculate hours between two time strings"""
    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")
    
    # Handle overnight overtime
    if end < start:
        end = end.replace(day=end.day + 1)
    
    duration = (end - start).seconds / 3600
    return round(duration, 2)

def calculate_overtime_rate(base_salary: float = 50000) -> float:
    """Calculate overtime rate (1.5x hourly rate)"""
    hourly_rate = (base_salary / 52 / 40)  # Assuming 40-hour work week
    return round(hourly_rate * 1.5, 2)

def init_sample_data():
    now = datetime.now()
    
    sample_requests = [
        {
            "id": "ot-001",
            "employeeId": "emp-1",
            "employeeName": "Mike Johnson",
            "department": "Maintenance",
            "date": (now - timedelta(days=5)).strftime("%Y-%m-%d"),
            "startTime": "18:00",
            "endTime": "22:00",
            "totalHours": 4.0,
            "reason": "Emergency equipment repair",
            "status": "approved",
            "rate": 45.50,
            "totalAmount": 182.00,
            "approvedBy": "manager-1",
            "approvedAt": (now - timedelta(days=4)).isoformat(),
            "createdAt": (now - timedelta(days=6)).isoformat(),
            "updatedAt": (now - timedelta(days=4)).isoformat()
        },
        {
            "id": "ot-002",
            "employeeId": "emp-2",
            "employeeName": "Sarah Chen",
            "department": "Operations",
            "date": (now - timedelta(days=3)).strftime("%Y-%m-%d"),
            "startTime": "20:00",
            "endTime": "02:00",
            "totalHours": 6.0,
            "reason": "Production line setup",
            "status": "approved",
            "rate": 42.75,
            "totalAmount": 256.50,
            "approvedBy": "manager-1",
            "approvedAt": (now - timedelta(days=2)).isoformat(),
            "createdAt": (now - timedelta(days=4)).isoformat(),
            "updatedAt": (now - timedelta(days=2)).isoformat()
        },
        {
            "id": "ot-003",
            "employeeId": "emp-3",
            "employeeName": "David Rodriguez",
            "department": "IT",
            "date": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
            "startTime": "19:00",
            "endTime": "23:00",
            "totalHours": 4.0,
            "reason": "System maintenance",
            "status": "pending",
            "rate": 48.25,
            "totalAmount": 193.00,
            "approvedBy": None,
            "approvedAt": None,
            "createdAt": (now - timedelta(days=1)).isoformat(),
            "updatedAt": (now - timedelta(days=1)).isoformat()
        },
        {
            "id": "ot-004",
            "employeeId": "emp-1",
            "employeeName": "Mike Johnson",
            "department": "Maintenance",
            "date": (now - timedelta(days=10)).strftime("%Y-%m-%d"),
            "startTime": "17:00",
            "endTime": "21:30",
            "totalHours": 4.5,
            "reason": "Preventive maintenance",
            "status": "paid",
            "rate": 45.50,
            "totalAmount": 204.75,
            "approvedBy": "manager-1",
            "approvedAt": (now - timedelta(days=9)).isoformat(),
            "createdAt": (now - timedelta(days=11)).isoformat(),
            "updatedAt": (now - timedelta(days=8)).isoformat()
        },
        {
            "id": "ot-005",
            "employeeId": "emp-4",
            "employeeName": "Emily Watson",
            "department": "Quality Control",
            "date": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
            "startTime": "16:00",
            "endTime": "20:00",
            "totalHours": 4.0,
            "reason": "Quality audit preparation",
            "status": "rejected",
            "rate": 40.80,
            "totalAmount": 163.20,
            "approvedBy": "manager-2",
            "approvedAt": (now - timedelta(days=6)).isoformat(),
            "createdAt": (now - timedelta(days=8)).isoformat(),
            "updatedAt": (now - timedelta(days=6)).isoformat()
        }
    ]
    
    for request in sample_requests:
        overtime_db[request["id"]] = request

# Initialize sample data
init_sample_data()

@router.get("/requests", response_model=List[OvertimeRequest])
async def get_overtime_requests(
    employee_id: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get all overtime requests with optional filtering"""
    requests = list(overtime_db.values())
    
    # Apply filters
    if employee_id:
        requests = [req for req in requests if req["employeeId"] == employee_id]
    if department:
        requests = [req for req in requests if req["department"] == department]
    if status:
        requests = [req for req in requests if req["status"] == status]
    if start_date:
        requests = [req for req in requests if req["date"] >= start_date]
    if end_date:
        requests = [req for req in requests if req["date"] <= end_date]
    
    return requests

@router.get("/requests/{request_id}", response_model=OvertimeRequest)
async def get_overtime_request(request_id: str):
    """Get a specific overtime request by ID"""
    if request_id not in overtime_db:
        raise HTTPException(status_code=404, detail="Overtime request not found")
    return overtime_db[request_id]

@router.post("/requests", response_model=OvertimeRequest)
async def create_overtime_request(request: OvertimeRequestCreate):
    """Create a new overtime request"""
    # In a real app, you'd get employee details from your employees API
    employee_mapping = {
        "emp-1": {"name": "Mike Johnson", "department": "Maintenance", "salary": 50000},
        "emp-2": {"name": "Sarah Chen", "department": "Operations", "salary": 48000},
        "emp-3": {"name": "David Rodriguez", "department": "IT", "salary": 52000},
        "emp-4": {"name": "Emily Watson", "department": "Quality Control", "salary": 45000},
        "emp-5": {"name": "James Wilson", "department": "Security", "salary": 42000}
    }
    
    employee_info = employee_mapping.get(request.employeeId, {
        "name": "Unknown Employee", 
        "department": "Unknown", 
        "salary": 40000
    })
    
    # Calculate overtime details
    total_hours = calculate_overtime_hours(request.startTime, request.endTime)
    rate = calculate_overtime_rate(employee_info["salary"])
    total_amount = round(total_hours * rate, 2)
    
    request_id = f"ot-{len(overtime_db) + 1:03d}"
    now = datetime.now().isoformat()
    
    new_request = OvertimeRequest(
        id=request_id,
        employeeId=request.employeeId,
        employeeName=employee_info["name"],
        department=employee_info["department"],
        date=request.date,
        startTime=request.startTime,
        endTime=request.endTime,
        totalHours=total_hours,
        reason=request.reason,
        status=OvertimeStatus.PENDING,
        rate=rate,
        totalAmount=total_amount,
        approvedBy=None,
        approvedAt=None,
        createdAt=now,
        updatedAt=now
    )
    
    overtime_db[request_id] = new_request.dict()
    return new_request

@router.put("/requests/{request_id}", response_model=OvertimeRequest)
async def update_overtime_request(request_id: str, request_update: OvertimeRequestUpdate):
    """Update an existing overtime request"""
    if request_id not in overtime_db:
        raise HTTPException(status_code=404, detail="Overtime request not found")
    
    existing_request = overtime_db[request_id]
    update_data = request_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        if value is not None:
            existing_request[field] = value
    
    # Recalculate hours if times changed
    if 'startTime' in update_data or 'endTime' in update_data:
        existing_request['totalHours'] = calculate_overtime_hours(
            existing_request['startTime'],
            existing_request['endTime']
        )
        existing_request['totalAmount'] = round(
            existing_request['totalHours'] * existing_request['rate'], 
            2
        )
    
    # Set approved timestamp if status changed to approved
    if 'status' in update_data and update_data['status'] == OvertimeStatus.APPROVED:
        existing_request['approvedAt'] = datetime.now().isoformat()
    
    existing_request['updatedAt'] = datetime.now().isoformat()
    overtime_db[request_id] = existing_request
    
    return existing_request

@router.delete("/requests/{request_id}")
async def delete_overtime_request(request_id: str):
    """Delete an overtime request"""
    if request_id not in overtime_db:
        raise HTTPException(status_code=404, detail="Overtime request not found")
    
    del overtime_db[request_id]
    return {"message": "Overtime request deleted successfully"}

@router.post("/requests/{request_id}/approve")
async def approve_overtime_request(request_id: str, approved_by: str):
    """Approve an overtime request"""
    if request_id not in overtime_db:
        raise HTTPException(status_code=404, detail="Overtime request not found")
    
    request = overtime_db[request_id]
    request['status'] = OvertimeStatus.APPROVED
    request['approvedBy'] = approved_by
    request['approvedAt'] = datetime.now().isoformat()
    request['updatedAt'] = datetime.now().isoformat()
    
    overtime_db[request_id] = request
    return {"message": "Overtime request approved", "request": request}

@router.post("/requests/{request_id}/reject")
async def reject_overtime_request(request_id: str):
    """Reject an overtime request"""
    if request_id not in overtime_db:
        raise HTTPException(status_code=404, detail="Overtime request not found")
    
    request = overtime_db[request_id]
    request['status'] = OvertimeStatus.REJECTED
    request['updatedAt'] = datetime.now().isoformat()
    
    overtime_db[request_id] = request
    return {"message": "Overtime request rejected", "request": request}

@router.post("/requests/{request_id}/mark-paid")
async def mark_overtime_paid(request_id: str):
    """Mark overtime request as paid"""
    if request_id not in overtime_db:
        raise HTTPException(status_code=404, detail="Overtime request not found")
    
    request = overtime_db[request_id]
    if request['status'] != OvertimeStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only approved overtime requests can be marked as paid")
    
    request['status'] = OvertimeStatus.PAID
    request['updatedAt'] = datetime.now().isoformat()
    
    overtime_db[request_id] = request
    return {"message": "Overtime marked as paid", "request": request}

@router.get("/stats")
async def get_overtime_stats():
    """Get overtime statistics for dashboard"""
    requests = list(overtime_db.values())
    
    total_requests = len(requests)
    pending_requests = len([req for req in requests if req['status'] == 'pending'])
    approved_requests = len([req for req in requests if req['status'] == 'approved'])
    paid_requests = len([req for req in requests if req['status'] == 'paid'])
    
    total_hours = sum(req['totalHours'] for req in requests if req['status'] in ['approved', 'paid'])
    total_amount = sum(req['totalAmount'] for req in requests if req['status'] in ['approved', 'paid'])
    
    # Current month stats
    current_month = datetime.now().month
    current_year = datetime.now().year
    current_month_requests = [
        req for req in requests 
        if datetime.strptime(req['date'], "%Y-%m-%d").month == current_month
        and datetime.strptime(req['date'], "%Y-%m-%d").year == current_year
    ]
    current_month_hours = sum(req['totalHours'] for req in current_month_requests)
    current_month_amount = sum(req['totalAmount'] for req in current_month_requests)
    
    # Department distribution
    departments = {}
    for request in requests:
        dept = request['department']
        if dept not in departments:
            departments[dept] = 0
        departments[dept] += request['totalHours']
    
    return {
        "totalRequests": total_requests,
        "pendingRequests": pending_requests,
        "approvedRequests": approved_requests,
        "paidRequests": paid_requests,
        "totalHours": round(total_hours, 2),
        "totalAmount": round(total_amount, 2),
        "currentMonthHours": round(current_month_hours, 2),
        "currentMonthAmount": round(current_month_amount, 2),
        "departmentDistribution": departments
    }

@router.get("/employees/{employee_id}/requests")
async def get_employee_overtime_requests(employee_id: str):
    """Get all overtime requests for a specific employee"""
    employee_requests = [
        req for req in overtime_db.values() 
        if req["employeeId"] == employee_id
    ]
    
    total_hours = sum(req['totalHours'] for req in employee_requests if req['status'] in ['approved', 'paid'])
    total_amount = sum(req['totalAmount'] for req in employee_requests if req['status'] in ['approved', 'paid'])
    
    return {
        "employeeId": employee_id,
        "employeeName": employee_requests[0]["employeeName"] if employee_requests else "Unknown",
        "totalRequests": len(employee_requests),
        "totalHours": round(total_hours, 2),
        "totalAmount": round(total_amount, 2),
        "requests": sorted(employee_requests, key=lambda x: x['date'], reverse=True)
    }

@router.get("/departments")
async def get_departments():
    """Get all departments with overtime requests"""
    departments = set(req['department'] for req in overtime_db.values())
    return {"departments": sorted(list(departments))}

@router.get("/upcoming")
async def get_upcoming_overtime(days: int = 7):
    """Get upcoming overtime requests within the next specified days"""
    today = datetime.now().strftime("%Y-%m-%d")
    future_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    
    upcoming_requests = [
        req for req in overtime_db.values()
        if today <= req['date'] <= future_date and req['status'] == 'approved'
    ]
    
    return {
        "count": len(upcoming_requests),
        "upcomingRequests": sorted(upcoming_requests, key=lambda x: x['date'])
    }

@router.get("/statuses")
async def get_overtime_statuses():
    """Get all available overtime statuses"""
    return {"statuses": [status.value for status in OvertimeStatus]}