from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
from app.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Models – removed department and manager_name
class LeaveCreate(BaseModel):
    employee_name: str = Field(..., min_length=1)
    employee_id: str = Field(..., min_length=1)
    position: str = Field(..., min_length=1)
    leave_type: str = Field(...)
    start_date: date = Field(...)
    end_date: date = Field(...)
    reason: str = Field(..., min_length=1)
    contact_number: str = Field(..., min_length=1)
    emergency_contact: Optional[str] = None
    handover_to: Optional[str] = None

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class LeaveUpdate(BaseModel):
    employee_name: Optional[str] = None
    employee_id: Optional[str] = None
    position: Optional[str] = None
    leave_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None
    contact_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    handover_to: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v is not None and values.get('start_date') is not None and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v

# Helper functions
def calculate_total_days(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1

def get_supabase_data(response):
    if hasattr(response, 'data'):
        return response.data
    return response

# POST create leave
@router.post("")
@router.post("/")
async def create_leave(leave: LeaveCreate):
    try:
        total_days = calculate_total_days(leave.start_date, leave.end_date)
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
        result = supabase.table("leaves").insert(data_to_insert).execute()
        created_data = get_supabase_data(result)
        if not created_data:
            raise HTTPException(status_code=500, detail="No data returned after insertion")
        return created_data[0]
    except Exception as e:
        logger.error(f"Error creating leave: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating leave: {str(e)}")

# GET all leaves (optional filters)
@router.get("")
@router.get("/")
async def get_leaves(status: Optional[str] = None, leave_type: Optional[str] = None):
    try:
        query = supabase.table("leaves").select("*")
        if status:
            query = query.eq("status", status)
        if leave_type:
            query = query.eq("leave_type", leave_type)
        response = query.order("applied_date", desc=True).execute()
        data = get_supabase_data(response)
        return data or []
    except Exception as e:
        logger.error(f"Error fetching leaves: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching leaves: {str(e)}")

# GET stats
@router.get("/stats/summary")
async def get_leave_stats():
    try:
        response = supabase.table("leaves").select("*").execute()
        data = get_supabase_data(response) or []
        today = date.today().isoformat()
        total = len(data)
        pending = sum(1 for l in data if l.get('status') == 'pending')
        approved = sum(1 for l in data if l.get('status') == 'approved')
        rejected = sum(1 for l in data if l.get('status') == 'rejected')
        on_leave_now = sum(1 for l in data if l.get('status') == 'approved' and l.get('start_date') <= today <= l.get('end_date'))
        upcoming = sum(1 for l in data if l.get('status') == 'approved' and l.get('start_date') > today)
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "on_leave_now": on_leave_now,
            "upcoming": upcoming
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "on_leave_now": 0, "upcoming": 0}

# GET leave balance (mock)
@router.get("/balance/{employee_id}")
async def get_leave_balance(employee_id: str):
    # Mock – replace with real logic
    return {
        "annual": {"total": 21, "used": 0, "pending": 0, "remaining": 21},
        "sick": {"total": 10, "used": 0, "pending": 0, "remaining": 10},
        "emergency": {"total": 5, "used": 0, "pending": 0, "remaining": 5},
        "compassionate": {"total": 5, "used": 0, "pending": 0, "remaining": 5},
        "maternity": {"total": 90, "used": 0, "pending": 0, "remaining": 90},
        "study": {"total": 10, "used": 0, "pending": 0, "remaining": 10}
    }

# PATCH update leave
@router.patch("/{leave_id}")
async def update_leave(leave_id: int, updated: LeaveUpdate):
    try:
        # Check existence
        existing_response = supabase.table("leaves").select("*").eq("id", leave_id).execute()
        existing_data = get_supabase_data(existing_response)
        if not existing_data:
            raise HTTPException(status_code=404, detail=f"Leave with ID {leave_id} not found")

        # Build update dict with only provided fields
        data_to_update = updated.dict(exclude_unset=True)

        # Recalculate total_days if dates changed
        if 'start_date' in data_to_update or 'end_date' in data_to_update:
            current = existing_data[0]
            start = data_to_update.get('start_date', date.fromisoformat(current['start_date']))
            end = data_to_update.get('end_date', date.fromisoformat(current['end_date']))
            data_to_update['total_days'] = calculate_total_days(start, end)

        # Convert date objects to ISO strings
        if 'start_date' in data_to_update and isinstance(data_to_update['start_date'], date):
            data_to_update['start_date'] = data_to_update['start_date'].isoformat()
        if 'end_date' in data_to_update and isinstance(data_to_update['end_date'], date):
            data_to_update['end_date'] = data_to_update['end_date'].isoformat()

        # Remove fields that are not in the table (if any were accidentally sent)
        # (We've removed department and manager_name from models, so none should be here)
        # However, if frontend still sends them (they are not in models now, so won't be in dict)

        if not data_to_update:
            return existing_data[0]

        # Perform update
        result = supabase.table("leaves").update(data_to_update).eq("id", leave_id).execute()
        updated_data = get_supabase_data(result)

        if not updated_data:
            # Fallback fetch
            fetch_response = supabase.table("leaves").select("*").eq("id", leave_id).execute()
            fetched = get_supabase_data(fetch_response)
            if fetched:
                return fetched[0]
            else:
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
    try:
        existing_response = supabase.table("leaves").select("id, employee_name, employee_id").eq("id", leave_id).execute()
        existing_data = get_supabase_data(existing_response)
        if not existing_data:
            raise HTTPException(status_code=404, detail=f"Leave with ID {leave_id} not found")
        employee_info = f"{existing_data[0].get('employee_name', '')} ({existing_data[0].get('employee_id', '')})"
        supabase.table("leaves").delete().eq("id", leave_id).execute()
        return {"success": True, "detail": f"Leave {leave_id} for {employee_info} deleted", "deleted_id": leave_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting leave {leave_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting leave: {str(e)}")