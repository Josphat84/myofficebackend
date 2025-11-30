# backend/app/routers/leaves.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
from app.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class LeaveCreate(BaseModel):
    employee_name: str = Field(..., min_length=1, description="Full name of the employee")
    employee_id: str = Field(..., min_length=1, description="Employee ID")
    position: str = Field(..., min_length=1, description="Job position")
    leave_type: str = Field(..., description="Type of leave")
    start_date: date = Field(..., description="Leave start date")
    end_date: date = Field(..., description="Leave end date")
    reason: str = Field(..., min_length=1, description="Reason for leave")
    contact_number: str = Field(..., min_length=1, description="Contact number")
    emergency_contact: Optional[str] = Field(None, description="Emergency contact details")
    handover_to: Optional[str] = Field(None, description="Person to handover to")

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class LeaveUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Leave status")
    notes: Optional[str] = Field(None, description="Additional notes")

def calculate_total_days(start_date: date, end_date: date) -> int:
    """Calculate total days between start and end date (inclusive)"""
    return (end_date - start_date).days + 1

def get_supabase_data(response):
    """Helper to extract data from Supabase response"""
    if hasattr(response, 'data'):
        return response.data
    return response

# POST create leave
@router.post("")
@router.post("/")
async def create_leave(leave: LeaveCreate):
    """Create a new leave application."""
    try:
        logger.info(f"Creating leave for employee: {leave.employee_name}")
        
        # Calculate total days
        total_days = calculate_total_days(leave.start_date, leave.end_date)
        
        # Prepare data for insertion
        data_to_insert = {
            "employee_name": leave.employee_name,
            "employee_id": leave.employee_id,
            "position": leave.position,
            "leave_type": leave.leave_type,
            "start_date": leave.start_date.isoformat(),
            "end_date": leave.end_date.isoformat(),
            "total_days": total_days,
            "reason": leave.reason,
            "contact_number": leave.contact_number,
            "emergency_contact": leave.emergency_contact,
            "handover_to": leave.handover_to,
            "status": "pending",
            "applied_date": datetime.utcnow().isoformat(),
            "notes": ""
        }
        
        # Insert into Supabase
        result = supabase.table("leaves").insert(data_to_insert).execute()
        created_data = get_supabase_data(result)
            
        if not created_data:
            raise HTTPException(status_code=500, detail="No data returned after insertion")
            
        return created_data[0]
        
    except Exception as e:
        logger.error(f"Error creating leave: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating leave: {str(e)}")

# GET all leaves
@router.get("")
@router.get("/")
async def get_leaves(status: Optional[str] = None, leave_type: Optional[str] = None):
    """Retrieve all leaves from the database."""
    try:
        query = supabase.table("leaves").select("*")
        
        if status:
            query = query.eq("status", status)
        if leave_type:
            query = query.eq("leave_type", leave_type)
            
        response = query.order("applied_date", desc=True).execute()
        data = get_supabase_data(response)
        
        if not data:
            return []
        
        return data
    except Exception as e:
        logger.error(f"Error fetching leaves: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching leaves: {str(e)}")

# GET leave statistics
@router.get("/stats/summary")
async def get_leave_stats():
    """Get leave statistics summary."""
    try:
        # Get all leaves
        response = supabase.table("leaves").select("*").execute()
        data = get_supabase_data(response)
        
        if not data:
            return {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "on_leave_now": 0,
                "upcoming": 0
            }
        
        total = len(data)
        pending = len([l for l in data if l.get('status') == 'pending'])
        approved = len([l for l in data if l.get('status') == 'approved'])
        rejected = len([l for l in data if l.get('status') == 'rejected'])
        
        # Calculate on leave now (approved leaves where current date is between start and end date)
        today = date.today().isoformat()
        on_leave_now = len([
            l for l in data 
            if l.get('status') == 'approved' 
            and l.get('start_date') <= today 
            and l.get('end_date') >= today
        ])
        
        # Upcoming leaves (approved leaves starting in the future)
        upcoming = len([
            l for l in data 
            if l.get('status') == 'approved' 
            and l.get('start_date') > today
        ])
        
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "on_leave_now": on_leave_now,
            "upcoming": upcoming
        }
        
    except Exception as e:
        logger.error(f"Error fetching leave stats: {str(e)}")
        return {
            "total": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "on_leave_now": 0,
            "upcoming": 0
        }

# GET leave balance
@router.get("/balance/{employee_id}")
async def get_leave_balance(employee_id: str):
    """Get leave balance for an employee."""
    try:
        # Mock balance data
        return {
            "annual": {"total": 21, "used": 0, "pending": 0, "remaining": 21},
            "sick": {"total": 10, "used": 0, "pending": 0, "remaining": 10},
            "emergency": {"total": 5, "used": 0, "pending": 0, "remaining": 5},
            "compassionate": {"total": 5, "used": 0, "pending": 0, "remaining": 5},
            "maternity": {"total": 90, "used": 0, "pending": 0, "remaining": 90},
            "study": {"total": 10, "used": 0, "pending": 0, "remaining": 10}
        }
        
    except Exception as e:
        logger.error(f"Error fetching leave balance: {str(e)}")
        return {
            "annual": {"total": 21, "used": 0, "pending": 0, "remaining": 21},
            "sick": {"total": 10, "used": 0, "pending": 0, "remaining": 10},
            "emergency": {"total": 5, "used": 0, "pending": 0, "remaining": 5},
            "compassionate": {"total": 5, "used": 0, "pending": 0, "remaining": 5},
            "maternity": {"total": 90, "used": 0, "pending": 0, "remaining": 90},
            "study": {"total": 10, "used": 0, "pending": 0, "remaining": 10}
        }

# PATCH update leave status
@router.patch("/{leave_id}")
async def update_leave(leave_id: int, updated: LeaveUpdate):
    """Update an existing leave application status."""
    try:
        # Check if leave exists
        existing_response = supabase.table("leaves").select("*").eq("id", leave_id).execute()
        existing_data = get_supabase_data(existing_response)
            
        if not existing_data:
            raise HTTPException(status_code=404, detail=f"Leave with ID {leave_id} not found")
        
        # Prepare data for update
        data_to_update = updated.dict(exclude_unset=True)
        
        result = supabase.table("leaves").update(data_to_update).eq("id", leave_id).execute()
        updated_data = get_supabase_data(result)
            
        if not updated_data:
            raise HTTPException(status_code=500, detail="No data returned after update")
            
        return updated_data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating leave {leave_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating leave: {str(e)}")

# DELETE leave
@router.delete("/{leave_id}")
async def delete_leave(leave_id: int):
    """Delete a leave application."""
    try:
        existing_response = supabase.table("leaves").select("id, employee_name, employee_id").eq("id", leave_id).execute()
        existing_data = get_supabase_data(existing_response)
            
        if not existing_data:
            raise HTTPException(status_code=404, detail=f"Leave with ID {leave_id} not found")
        
        employee_info = f"{existing_data[0].get('employee_name', '')} ({existing_data[0].get('employee_id', '')})"
        
        supabase.table("leaves").delete().eq("id", leave_id).execute()
            
        return {
            "success": True,
            "detail": f"Leave application {leave_id} for {employee_info} successfully deleted",
            "deleted_id": leave_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting leave {leave_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting leave: {str(e)}")