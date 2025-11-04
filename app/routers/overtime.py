# backend/app/routers/overtime.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum
from app.supabase_client import supabase
import logging

# Define router WITHOUT prefix (prefix will be added in main.py)
router = APIRouter(tags=["overtime"])

# Pydantic models
class OvertimeStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"

class OvertimeRequest(BaseModel):
    id: str
    employee_id: str  # Changed back to string for alphanumeric IDs
    employee_name: str
    department: str
    date: str
    start_time: str
    end_time: str
    hours: float
    reason: str
    overtime_type: str
    status: OvertimeStatus
    manager_comments: Optional[str] = None
    created_at: str
    updated_at: str

class OvertimeRequestCreate(BaseModel):
    employee_id: str  # Changed back to string for alphanumeric IDs
    date: str
    start_time: str
    end_time: str
    reason: str
    overtime_type: str = "planned"
    status: str = "pending"

class OvertimeRequestUpdate(BaseModel):
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reason: Optional[str] = None
    overtime_type: Optional[str] = None
    status: Optional[str] = None
    manager_comments: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str
    comments: Optional[str] = None

def calculate_overtime_hours(start_time: str, end_time: str) -> float:
    """Calculate hours between two time strings"""
    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")
        
        # Handle overnight overtime
        if end < start:
            end = end.replace(day=end.day + 1)
        
        duration = (end - start).seconds / 3600
        return round(duration, 2)
    except Exception as e:
        logging.error(f"Error calculating overtime hours: {e}")
        return 0.0

async def get_employee_details(employee_id: str):
    """Get employee details from Supabase using alphanumeric employee_id"""
    try:
        response = supabase.table("employees") \
            .select("id, employee_id, first_name, last_name, department, designation") \
            .eq("employee_id", employee_id) \
            .execute()
        
        if not response.data:
            return None
        
        employee = response.data[0]
        return {
            "id": employee.get("id"),
            "employee_id": employee.get("employee_id", ""),
            "first_name": employee.get("first_name", ""),
            "last_name": employee.get("last_name", ""),
            "department": employee.get("department", ""),
            "designation": employee.get("designation", "")
        }
    except Exception as e:
        logging.error(f"Error fetching employee details: {e}")
        return None

# Test endpoints
@router.get("/test")
async def test_overtime():
    return {"message": "Overtime router is working!"}

@router.get("/health")
async def overtime_health():
    return {
        "status": "healthy", 
        "router": "overtime",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/", response_model=List[OvertimeRequest])
async def get_overtime_requests(
    employee_id: Optional[str] = None,  # Changed back to string
    department: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get all overtime requests with optional filtering"""
    try:
        query = supabase.table("overtime_requests") \
            .select("*, employees(first_name, last_name, department, designation)") \
            .order("created_at", desc=True)
        
        # Apply filters
        if employee_id:
            query = query.eq("employee_id", employee_id)
        if department:
            query = query.eq("department", department)
        if status:
            query = query.eq("status", status)
        if start_date:
            query = query.gte("date", start_date)
        if end_date:
            query = query.lte("date", end_date)
        
        response = query.execute()
        
        if response.data is None:
            return []
        
        # Transform the data to match frontend expectations
        transformed_data = []
        for request in response.data:
            employee = request.get('employees', {})
            transformed_data.append({
                'id': request['id'],
                'employee_id': request['employee_id'],  # This is now alphanumeric
                'employee_name': f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
                'department': employee.get('department', '') or request.get('department', ''),
                'date': request['date'],
                'start_time': request['start_time'],
                'end_time': request['end_time'],
                'hours': float(request['hours']),
                'reason': request['reason'],
                'overtime_type': request['overtime_type'],
                'status': request['status'],
                'manager_comments': request.get('manager_comments'),
                'created_at': request['created_at'],
                'updated_at': request['updated_at']
            })
        
        return transformed_data
        
    except Exception as e:
        logging.error(f"Error fetching overtime requests: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch overtime requests")

@router.post("/", response_model=OvertimeRequest)
async def create_overtime_request(request: OvertimeRequestCreate):
    """Create a new overtime request"""
    try:
        # Verify employee exists and get details
        employee_details = await get_employee_details(request.employee_id)
        if not employee_details:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Calculate hours
        hours = calculate_overtime_hours(request.start_time, request.end_time)
        if hours <= 0:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        
        # Create the overtime request
        insert_data = {
            'employee_id': request.employee_id,  # Alphanumeric employee ID
            'date': request.date,
            'start_time': request.start_time,
            'end_time': request.end_time,
            'hours': hours,
            'reason': request.reason,
            'overtime_type': request.overtime_type,
            'status': request.status,
            'department': employee_details['department']
        }
        
        response = supabase.table("overtime_requests") \
            .insert(insert_data) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create overtime request")
        
        # Return the created record
        created_request = response.data[0]
        
        return {
            'id': created_request['id'],
            'employee_id': created_request['employee_id'],
            'employee_name': f"{employee_details['first_name']} {employee_details['last_name']}",
            'department': employee_details['department'],
            'date': created_request['date'],
            'start_time': created_request['start_time'],
            'end_time': created_request['end_time'],
            'hours': float(created_request['hours']),
            'reason': created_request['reason'],
            'overtime_type': created_request['overtime_type'],
            'status': created_request['status'],
            'manager_comments': created_request.get('manager_comments'),
            'created_at': created_request['created_at'],
            'updated_at': created_request['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating overtime request: {e}")
        raise HTTPException(status_code=500, detail="Failed to create overtime request")

@router.get("/{request_id}", response_model=OvertimeRequest)
async def get_overtime_request(request_id: str):
    """Get a specific overtime request by ID"""
    try:
        response = supabase.table("overtime_requests") \
            .select("*, employees(first_name, last_name, department, designation)") \
            .eq("id", request_id) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Overtime request not found")
        
        request = response.data[0]
        employee = request.get('employees', {})
        
        return {
            'id': request['id'],
            'employee_id': request['employee_id'],  # This is now alphanumeric
            'employee_name': f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
            'department': employee.get('department', '') or request.get('department', ''),
            'date': request['date'],
            'start_time': request['start_time'],
            'end_time': request['end_time'],
            'hours': float(request['hours']),
            'reason': request['reason'],
            'overtime_type': request['overtime_type'],
            'status': request['status'],
            'manager_comments': request.get('manager_comments'),
            'created_at': request['created_at'],
            'updated_at': request['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching overtime request: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch overtime request")

@router.put("/{request_id}", response_model=OvertimeRequest)
async def update_overtime_request(request_id: str, request_update: OvertimeRequestUpdate):
    """Update an existing overtime request"""
    try:
        update_data = {k: v for k, v in request_update.dict().items() if v is not None}
        
        # Recalculate hours if times are updated
        if 'start_time' in update_data or 'end_time' in update_data:
            # Get current request to calculate new hours
            current_response = supabase.table("overtime_requests") \
                .select("start_time, end_time") \
                .eq("id", request_id) \
                .execute()
            
            if not current_response.data:
                raise HTTPException(status_code=404, detail="Overtime request not found")
            
            current_request = current_response.data[0]
            start_time = update_data.get('start_time', current_request['start_time'])
            end_time = update_data.get('end_time', current_request['end_time'])
            
            hours = calculate_overtime_hours(start_time, end_time)
            if hours <= 0:
                raise HTTPException(status_code=400, detail="End time must be after start time")
            
            update_data['hours'] = hours
        
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = supabase.table("overtime_requests") \
            .update(update_data) \
            .eq("id", request_id) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Overtime request not found")
        
        # Return updated record
        updated_response = supabase.table("overtime_requests") \
            .select("*, employees(first_name, last_name, department, designation)") \
            .eq("id", request_id) \
            .execute()
        
        if not updated_response.data:
            raise HTTPException(status_code=404, detail="Overtime request not found after update")
        
        request = updated_response.data[0]
        employee = request.get('employees', {})
        
        return {
            'id': request['id'],
            'employee_id': request['employee_id'],  # This is now alphanumeric
            'employee_name': f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
            'department': employee.get('department', '') or request.get('department', ''),
            'date': request['date'],
            'start_time': request['start_time'],
            'end_time': request['end_time'],
            'hours': float(request['hours']),
            'reason': request['reason'],
            'overtime_type': request['overtime_type'],
            'status': request['status'],
            'manager_comments': request.get('manager_comments'),
            'created_at': request['created_at'],
            'updated_at': request['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating overtime request: {e}")
        raise HTTPException(status_code=500, detail="Failed to update overtime request")

@router.delete("/{request_id}")
async def delete_overtime_request(request_id: str):
    """Delete an overtime request"""
    try:
        response = supabase.table("overtime_requests") \
            .delete() \
            .eq("id", request_id) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Overtime request not found")
        
        return {"message": "Overtime request deleted successfully"}
        
    except Exception as e:
        logging.error(f"Error deleting overtime request: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete overtime request")

@router.patch("/{request_id}/status")
async def update_overtime_status(request_id: str, status_update: StatusUpdate):
    """Update overtime request status"""
    try:
        update_data = {
            'status': status_update.status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if status_update.comments:
            update_data['manager_comments'] = status_update.comments
        
        response = supabase.table("overtime_requests") \
            .update(update_data) \
            .eq("id", request_id) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Overtime request not found")
        
        return {"message": f"Overtime request {status_update.status}", "request": response.data[0]}
        
    except Exception as e:
        logging.error(f"Error updating overtime status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update overtime status")

@router.get("/stats/summary")
async def get_overtime_stats():
    """Get overtime statistics for dashboard"""
    try:
        # Get all overtime requests
        response = supabase.table("overtime_requests") \
            .select("*") \
            .execute()
        
        if response.data is None:
            return {
                "total_requests": 0,
                "pending_requests": 0,
                "approved_requests": 0,
                "rejected_requests": 0,
                "total_hours": 0,
                "department_distribution": {}
            }
        
        requests = response.data
        
        total_requests = len(requests)
        pending_requests = len([req for req in requests if req['status'] == 'pending'])
        approved_requests = len([req for req in requests if req['status'] == 'approved'])
        rejected_requests = len([req for req in requests if req['status'] == 'rejected'])
        
        total_hours = sum(req['hours'] for req in requests if req['status'] in ['approved'])
        
        # Department distribution
        departments = {}
        for request in requests:
            dept = request.get('department', 'Unknown')
            if dept not in departments:
                departments[dept] = 0
            if request['status'] == 'approved':
                departments[dept] += request['hours']
        
        return {
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "total_hours": round(total_hours, 2),
            "department_distribution": departments
        }
        
    except Exception as e:
        logging.error(f"Error fetching overtime stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch overtime statistics")