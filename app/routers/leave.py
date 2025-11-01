# backend/app/routers/leave.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum

router = APIRouter(prefix="/api/leave", tags=["leave"])

# Pydantic models
class LeaveType(str, Enum):
    VACATION = "vacation"
    SICK = "sick"
    PERSONAL = "personal"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    BEREAVEMENT = "bereavement"
    UNPAID = "unpaid"

class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class LeaveRequest(BaseModel):
    id: str
    employeeId: str
    employeeName: str
    leaveType: LeaveType
    startDate: str
    endDate: str
    totalDays: int
    reason: str
    status: LeaveStatus
    approvedBy: Optional[str] = None
    approvedAt: Optional[str] = None
    createdAt: str
    updatedAt: str

class LeaveRequestCreate(BaseModel):
    employeeId: str
    leaveType: LeaveType
    startDate: str
    endDate: str
    reason: str

class LeaveRequestUpdate(BaseModel):
    leaveType: Optional[LeaveType] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[LeaveStatus] = None
    approvedBy: Optional[str] = None

class LeaveBalance(BaseModel):
    employeeId: str
    employeeName: str
    vacationDays: int
    sickDays: int
    personalDays: int
    maternityDays: int
    paternityDays: int
    usedVacation: int
    usedSick: int
    usedPersonal: int
    usedMaternity: int
    usedPaternity: int

# Mock database
leave_requests_db = {}
leave_balances_db = {}

def calculate_leave_days(start_date: str, end_date: str) -> int:
    """Calculate business days between two dates (excluding weekends)"""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    business_days = 0
    current = start
    while current <= end:
        # Monday = 0, Sunday = 6
        if current.weekday() < 5:  # Monday to Friday
            business_days += 1
        current += timedelta(days=1)
    
    return business_days

def init_sample_data():
    now = datetime.now()
    
    # Sample leave balances
    sample_balances = [
        {
            "employeeId": "emp-1",
            "employeeName": "Mike Johnson",
            "vacationDays": 20,
            "sickDays": 10,
            "personalDays": 5,
            "maternityDays": 90,
            "paternityDays": 10,
            "usedVacation": 8,
            "usedSick": 2,
            "usedPersonal": 1,
            "usedMaternity": 0,
            "usedPaternity": 0
        },
        {
            "employeeId": "emp-2",
            "employeeName": "Sarah Chen",
            "vacationDays": 18,
            "sickDays": 10,
            "personalDays": 5,
            "maternityDays": 90,
            "paternityDays": 10,
            "usedVacation": 12,
            "usedSick": 1,
            "usedPersonal": 0,
            "usedMaternity": 0,
            "usedPaternity": 0
        },
        {
            "employeeId": "emp-3",
            "employeeName": "David Rodriguez",
            "vacationDays": 15,
            "sickDays": 10,
            "personalDays": 5,
            "maternityDays": 90,
            "paternityDays": 10,
            "usedVacation": 5,
            "usedSick": 3,
            "usedPersonal": 2,
            "usedMaternity": 0,
            "usedPaternity": 0
        }
    ]
    
    for balance in sample_balances:
        leave_balances_db[balance["employeeId"]] = balance
    
    # Sample leave requests
    sample_requests = [
        {
            "id": "leave-001",
            "employeeId": "emp-1",
            "employeeName": "Mike Johnson",
            "leaveType": "vacation",
            "startDate": (now + timedelta(days=10)).isoformat(),
            "endDate": (now + timedelta(days=14)).isoformat(),
            "totalDays": 5,
            "reason": "Family vacation",
            "status": "approved",
            "approvedBy": "manager-1",
            "approvedAt": (now - timedelta(days=2)).isoformat(),
            "createdAt": (now - timedelta(days=5)).isoformat(),
            "updatedAt": (now - timedelta(days=2)).isoformat()
        },
        {
            "id": "leave-002",
            "employeeId": "emp-2",
            "employeeName": "Sarah Chen",
            "leaveType": "sick",
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now + timedelta(days=2)).isoformat(),
            "totalDays": 3,
            "reason": "Flu recovery",
            "status": "approved",
            "approvedBy": "manager-1",
            "approvedAt": (now - timedelta(days=1)).isoformat(),
            "createdAt": (now - timedelta(days=2)).isoformat(),
            "updatedAt": (now - timedelta(days=1)).isoformat()
        },
        {
            "id": "leave-003",
            "employeeId": "emp-3",
            "employeeName": "David Rodriguez",
            "leaveType": "personal",
            "startDate": (now + timedelta(days=20)).isoformat(),
            "endDate": (now + timedelta(days=21)).isoformat(),
            "totalDays": 2,
            "reason": "Doctor appointment",
            "status": "pending",
            "approvedBy": None,
            "approvedAt": None,
            "createdAt": (now - timedelta(days=3)).isoformat(),
            "updatedAt": (now - timedelta(days=3)).isoformat()
        },
        {
            "id": "leave-004",
            "employeeId": "emp-1",
            "employeeName": "Mike Johnson",
            "leaveType": "vacation",
            "startDate": (now + timedelta(days=30)).isoformat(),
            "endDate": (now + timedelta(days=37)).isoformat(),
            "totalDays": 6,
            "reason": "Summer break",
            "status": "pending",
            "approvedBy": None,
            "approvedAt": None,
            "createdAt": (now - timedelta(days=1)).isoformat(),
            "updatedAt": (now - timedelta(days=1)).isoformat()
        }
    ]
    
    for request in sample_requests:
        leave_requests_db[request["id"]] = request

# Initialize sample data
init_sample_data()

@router.get("/requests", response_model=List[LeaveRequest])
async def get_leave_requests(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    leave_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get all leave requests with optional filtering"""
    requests = list(leave_requests_db.values())
    
    # Apply filters
    if employee_id:
        requests = [req for req in requests if req["employeeId"] == employee_id]
    if status:
        requests = [req for req in requests if req["status"] == status]
    if leave_type:
        requests = [req for req in requests if req["leaveType"] == leave_type]
    if start_date:
        start = datetime.fromisoformat(start_date)
        requests = [req for req in requests if datetime.fromisoformat(req["startDate"]) >= start]
    if end_date:
        end = datetime.fromisoformat(end_date)
        requests = [req for req in requests if datetime.fromisoformat(req["endDate"]) <= end]
    
    return requests

@router.get("/requests/{request_id}", response_model=LeaveRequest)
async def get_leave_request(request_id: str):
    """Get a specific leave request by ID"""
    if request_id not in leave_requests_db:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return leave_requests_db[request_id]

@router.post("/requests", response_model=LeaveRequest)
async def create_leave_request(request: LeaveRequestCreate):
    """Create a new leave request"""
    # Get employee name (in real app, this would come from employees API)
    employee_name = "Unknown Employee"
    for emp_id, balance in leave_balances_db.items():
        if emp_id == request.employeeId:
            employee_name = balance["employeeName"]
            break
    
    # Calculate total days
    total_days = calculate_leave_days(request.startDate, request.endDate)
    
    request_id = f"leave-{len(leave_requests_db) + 1:03d}"
    now = datetime.now().isoformat()
    
    new_request = LeaveRequest(
        id=request_id,
        employeeId=request.employeeId,
        employeeName=employee_name,
        leaveType=request.leaveType,
        startDate=request.startDate,
        endDate=request.endDate,
        totalDays=total_days,
        reason=request.reason,
        status=LeaveStatus.PENDING,
        approvedBy=None,
        approvedAt=None,
        createdAt=now,
        updatedAt=now
    )
    
    leave_requests_db[request_id] = new_request.dict()
    return new_request

@router.put("/requests/{request_id}", response_model=LeaveRequest)
async def update_leave_request(request_id: str, request_update: LeaveRequestUpdate):
    """Update an existing leave request"""
    if request_id not in leave_requests_db:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    existing_request = leave_requests_db[request_id]
    update_data = request_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        if value is not None:
            existing_request[field] = value
    
    # Recalculate days if dates changed
    if 'startDate' in update_data or 'endDate' in update_data:
        existing_request['totalDays'] = calculate_leave_days(
            existing_request['startDate'], 
            existing_request['endDate']
        )
    
    # Set approved timestamp if status changed to approved
    if 'status' in update_data and update_data['status'] == LeaveStatus.APPROVED:
        existing_request['approvedAt'] = datetime.now().isoformat()
        # Update leave balance when request is approved
        if existing_request['employeeId'] in leave_balances_db:
            balance = leave_balances_db[existing_request['employeeId']]
            leave_type = existing_request['leaveType']
            days = existing_request['totalDays']
            
            if leave_type == LeaveType.VACATION:
                balance['usedVacation'] += days
            elif leave_type == LeaveType.SICK:
                balance['usedSick'] += days
            elif leave_type == LeaveType.PERSONAL:
                balance['usedPersonal'] += days
            elif leave_type == LeaveType.MATERNITY:
                balance['usedMaternity'] += days
            elif leave_type == LeaveType.PATERNITY:
                balance['usedPaternity'] += days
    
    existing_request['updatedAt'] = datetime.now().isoformat()
    leave_requests_db[request_id] = existing_request
    
    return existing_request

@router.delete("/requests/{request_id}")
async def delete_leave_request(request_id: str):
    """Delete a leave request"""
    if request_id not in leave_requests_db:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    del leave_requests_db[request_id]
    return {"message": "Leave request deleted successfully"}

@router.post("/requests/{request_id}/approve")
async def approve_leave_request(request_id: str, approved_by: str):
    """Approve a leave request"""
    if request_id not in leave_requests_db:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    request = leave_requests_db[request_id]
    request['status'] = LeaveStatus.APPROVED
    request['approvedBy'] = approved_by
    request['approvedAt'] = datetime.now().isoformat()
    request['updatedAt'] = datetime.now().isoformat()
    
    # Update leave balance
    if request['employeeId'] in leave_balances_db:
        balance = leave_balances_db[request['employeeId']]
        leave_type = request['leaveType']
        days = request['totalDays']
        
        if leave_type == LeaveType.VACATION:
            balance['usedVacation'] += days
        elif leave_type == LeaveType.SICK:
            balance['usedSick'] += days
        elif leave_type == LeaveType.PERSONAL:
            balance['usedPersonal'] += days
        elif leave_type == LeaveType.MATERNITY:
            balance['usedMaternity'] += days
        elif leave_type == LeaveType.PATERNITY:
            balance['usedPaternity'] += days
    
    leave_requests_db[request_id] = request
    return {"message": "Leave request approved", "request": request}

@router.post("/requests/{request_id}/reject")
async def reject_leave_request(request_id: str):
    """Reject a leave request"""
    if request_id not in leave_requests_db:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    request = leave_requests_db[request_id]
    request['status'] = LeaveStatus.REJECTED
    request['updatedAt'] = datetime.now().isoformat()
    
    leave_requests_db[request_id] = request
    return {"message": "Leave request rejected", "request": request}

@router.post("/requests/{request_id}/cancel")
async def cancel_leave_request(request_id: str):
    """Cancel a leave request"""
    if request_id not in leave_requests_db:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    request = leave_requests_db[request_id]
    request['status'] = LeaveStatus.CANCELLED
    request['updatedAt'] = datetime.now().isoformat()
    
    leave_requests_db[request_id] = request
    return {"message": "Leave request cancelled", "request": request}

@router.get("/balances", response_model=List[LeaveBalance])
async def get_leave_balances(employee_id: Optional[str] = None):
    """Get leave balances for all employees or specific employee"""
    balances = list(leave_balances_db.values())
    
    if employee_id:
        balances = [balance for balance in balances if balance["employeeId"] == employee_id]
    
    return balances

@router.get("/balances/{employee_id}", response_model=LeaveBalance)
async def get_employee_leave_balance(employee_id: str):
    """Get leave balance for a specific employee"""
    if employee_id not in leave_balances_db:
        raise HTTPException(status_code=404, detail="Employee leave balance not found")
    return leave_balances_db[employee_id]

@router.get("/stats")
async def get_leave_stats():
    """Get leave statistics for dashboard"""
    requests = list(leave_requests_db.values())
    
    total_requests = len(requests)
    pending_requests = len([req for req in requests if req['status'] == 'pending'])
    approved_requests = len([req for req in requests if req['status'] == 'approved'])
    rejected_requests = len([req for req in requests if req['status'] == 'rejected'])
    
    # Requests by type
    by_type = {}
    for request in requests:
        leave_type = request['leaveType']
        by_type[leave_type] = by_type.get(leave_type, 0) + 1
    
    # Current month requests
    current_month = datetime.now().month
    current_year = datetime.now().year
    current_month_requests = len([
        req for req in requests 
        if datetime.fromisoformat(req['startDate']).month == current_month
        and datetime.fromisoformat(req['startDate']).year == current_year
    ])
    
    return {
        "totalRequests": total_requests,
        "pendingRequests": pending_requests,
        "approvedRequests": approved_requests,
        "rejectedRequests": rejected_requests,
        "currentMonthRequests": current_month_requests,
        "requestsByType": by_type
    }

@router.get("/employees")
async def get_employees_with_balances():
    """Get all employees with their leave balances"""
    employees = []
    for balance in leave_balances_db.values():
        # Calculate available days
        available_vacation = balance["vacationDays"] - balance["usedVacation"]
        available_sick = balance["sickDays"] - balance["usedSick"]
        available_personal = balance["personalDays"] - balance["usedPersonal"]
        available_maternity = balance["maternityDays"] - balance["usedMaternity"]
        available_paternity = balance["paternityDays"] - balance["usedPaternity"]
        
        employees.append({
            "id": balance["employeeId"],
            "name": balance["employeeName"],
            "availableVacation": max(0, available_vacation),
            "availableSick": max(0, available_sick),
            "availablePersonal": max(0, available_personal),
            "availableMaternity": max(0, available_maternity),
            "availablePaternity": max(0, available_paternity),
            "totalUsed": balance["usedVacation"] + balance["usedSick"] + balance["usedPersonal"] + balance["usedMaternity"] + balance["usedPaternity"]
        })
    
    return {"employees": employees}

@router.get("/upcoming")
async def get_upcoming_leave(days: int = 30):
    """Get upcoming leave requests within the next specified days"""
    now = datetime.now()
    future_date = now + timedelta(days=days)
    
    upcoming_requests = []
    
    for request in leave_requests_db.values():
        start_date = datetime.fromisoformat(request['startDate'])
        
        if now <= start_date <= future_date and request['status'] == 'approved':
            days_until = (start_date - now).days
            upcoming_requests.append({
                **request,
                "daysUntil": days_until
            })
    
    # Sort by start date
    upcoming_requests.sort(key=lambda x: x['startDate'])
    
    return {
        "count": len(upcoming_requests),
        "upcomingRequests": upcoming_requests
    }

@router.get("/types")
async def get_leave_types():
    """Get all available leave types"""
    return {"leaveTypes": [type.value for type in LeaveType]}

@router.get("/statuses")
async def get_leave_statuses():
    """Get all available leave statuses"""
    return {"statuses": [status.value for status in LeaveStatus]}