from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time
import logging
import json
from app.supabase_client import supabase

logger = logging.getLogger(__name__)
router = APIRouter()

# Custom JSON encoder to handle date and time objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, time):
            return obj.strftime('%H:%M')
        return super().default(obj)

# Pydantic Models
class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    rate: float = Field(..., gt=0)
    color: Optional[str] = None

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    rate: Optional[float] = None
    color: Optional[str] = None

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

class TimesheetEntryCreate(BaseModel):
    employee_id: int
    date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    break_minutes: int = Field(default=60)
    regular_hours: float = Field(default=0)
    overtime_hours: float = Field(default=0)
    holiday_overtime_hours: float = Field(default=0)
    total_hours: float = Field(default=0)
    status: str = Field(default="work")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

class TimesheetEntryUpdate(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    break_minutes: Optional[int] = None
    regular_hours: Optional[float] = None
    overtime_hours: Optional[float] = None
    holiday_overtime_hours: Optional[float] = None
    total_hours: Optional[float] = None
    status: Optional[str] = None

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

class HolidayCreate(BaseModel):
    date: date
    name: str = Field(..., min_length=1)

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

class LeaveDayCreate(BaseModel):
    employee_id: int
    date: date
    status: str = Field(..., min_length=1)

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

class BulkTimesheetUpdate(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    start_time: str
    end_time: str
    break_minutes: int = 60

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

# Helper function to convert dates in records
def convert_dates_to_iso(record):
    """Convert date objects to ISO format strings for JSON serialization"""
    if isinstance(record, dict):
        for key, value in record.items():
            if isinstance(value, (date, datetime)):
                record[key] = value.isoformat()
    return record

# Employees Endpoints
@router.get("/employees")
async def get_employees(
    department: Optional[str] = Query(None, alias="department"),
    active_only: bool = Query(True, alias="active_only")
):
    try:
        query = supabase.table("employees").select("*")
        
        if department and department != 'all':
            query = query.eq("department", department)
            
        response = query.order("name").execute()
        
        # Convert dates to ISO format for JSON serialization
        records = response.data or []
        for record in records:
            convert_dates_to_iso(record)
            
        return records
        
    except Exception as e:
        logger.error(f"Error fetching employees: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching employees: {str(e)}")

@router.post("/employees")
async def create_employee(employee: EmployeeCreate):
    try:
        data_to_insert = employee.dict()
        data_to_insert["created_at"] = datetime.utcnow().isoformat()
        data_to_insert["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("employees").insert(data_to_insert).execute()
        
        if response.data:
            result = response.data[0]
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to create employee")
            
    except Exception as e:
        logger.error(f"Error creating employee: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating employee: {str(e)}")

@router.get("/employees/{employee_id}")
async def get_employee(employee_id: int):
    try:
        response = supabase.table("employees").select("*").eq("id", employee_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        result = response.data[0]
        convert_dates_to_iso(result)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching employee: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching employee: {str(e)}")

@router.patch("/employees/{employee_id}")
async def update_employee(employee_id: int, updated: EmployeeUpdate):
    try:
        existing = supabase.table("employees").select("*").eq("id", employee_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        data_to_update = {k: v for k, v in updated.dict().items() if v is not None}
        data_to_update["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("employees").update(data_to_update).eq("id", employee_id).execute()
        
        if response.data:
            result = response.data[0]
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating employee: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating employee: {str(e)}")

@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: int):
    try:
        existing = supabase.table("employees").select("*").eq("id", employee_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Delete related timesheets and leave days first
        supabase.table("timesheets").delete().eq("employee_id", employee_id).execute()
        supabase.table("leave_days").delete().eq("employee_id", employee_id).execute()
        
        # Delete employee
        supabase.table("employees").delete().eq("id", employee_id).execute()
        return {"success": True, "message": "Employee deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting employee: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting employee: {str(e)}")

# Timesheets Endpoints
@router.get("/timesheets")
async def get_timesheets(
    employee_id: Optional[int] = Query(None, alias="employee_id"),
    start_date: Optional[date] = Query(None, alias="start_date"),
    end_date: Optional[date] = Query(None, alias="end_date"),
    department: Optional[str] = Query(None, alias="department")
):
    try:
        query = supabase.table("timesheets").select("*, employees(*)")
        
        if employee_id:
            query = query.eq("employee_id", employee_id)
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
        if department and department != 'all':
            # Join with employees table to filter by department
            employee_query = supabase.table("employees").select("id").eq("department", department).execute()
            employee_ids = [emp['id'] for emp in employee_query.data] if employee_query.data else []
            if employee_ids:
                query = query.in_("employee_id", employee_ids)
            
        response = query.order("date", desc=True).execute()
        
        # Convert dates to ISO format for JSON serialization
        records = response.data or []
        for record in records:
            convert_dates_to_iso(record)
            if record.get('employees'):
                convert_dates_to_iso(record['employees'])
            
        return records
        
    except Exception as e:
        logger.error(f"Error fetching timesheets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching timesheets: {str(e)}")

@router.post("/timesheets")
async def create_timesheet_entry(entry: TimesheetEntryCreate):
    try:
        data_to_insert = entry.dict()
        
        # Ensure dates are properly formatted for database
        if data_to_insert.get('date'):
            data_to_insert['date'] = data_to_insert['date'].isoformat()
            
        data_to_insert["created_at"] = datetime.utcnow().isoformat()
        data_to_insert["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("timesheets").insert(data_to_insert).execute()
        
        if response.data:
            result = response.data[0]
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to create timesheet entry")
            
    except Exception as e:
        logger.error(f"Error creating timesheet entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating timesheet entry: {str(e)}")

@router.post("/timesheets/bulk")
async def create_bulk_timesheet_entries(entries: List[TimesheetEntryCreate]):
    try:
        data_to_insert = []
        for entry in entries:
            entry_data = entry.dict()
            if entry_data.get('date'):
                entry_data['date'] = entry_data['date'].isoformat()
            entry_data["created_at"] = datetime.utcnow().isoformat()
            entry_data["updated_at"] = datetime.utcnow().isoformat()
            data_to_insert.append(entry_data)
        
        response = supabase.table("timesheets").insert(data_to_insert).execute()
        
        if response.data:
            results = response.data
            for result in results:
                convert_dates_to_iso(result)
            return results
        else:
            raise HTTPException(status_code=500, detail="Failed to create bulk timesheet entries")
            
    except Exception as e:
        logger.error(f"Error creating bulk timesheet entries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating bulk timesheet entries: {str(e)}")

@router.post("/timesheets/apply-shift")
async def apply_shift_to_range(bulk_update: BulkTimesheetUpdate):
    try:
        # Get all dates in the range
        start_date = bulk_update.start_date
        end_date = bulk_update.end_date
        current_date = start_date
        entries_to_create = []
        
        while current_date <= end_date:
            # Skip weekends (0=Sunday, 6=Saturday)
            if current_date.weekday() < 5:  # 0-4 = Monday to Friday
                entry = TimesheetEntryCreate(
                    employee_id=bulk_update.employee_id,
                    date=current_date,
                    start_time=bulk_update.start_time,
                    end_time=bulk_update.end_time,
                    break_minutes=bulk_update.break_minutes,
                    status="work"
                )
                entries_to_create.append(entry)
            
            current_date = current_date.replace(day=current_date.day + 1)
        
        # Create all entries
        return await create_bulk_timesheet_entries(entries_to_create)
        
    except Exception as e:
        logger.error(f"Error applying shift to range: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error applying shift to range: {str(e)}")

@router.get("/timesheets/{entry_id}")
async def get_timesheet_entry(entry_id: int):
    try:
        response = supabase.table("timesheets").select("*, employees(*)").eq("id", entry_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Timesheet entry not found")
        
        result = response.data[0]
        convert_dates_to_iso(result)
        if result.get('employees'):
            convert_dates_to_iso(result['employees'])
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timesheet entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching timesheet entry: {str(e)}")

@router.patch("/timesheets/{entry_id}")
async def update_timesheet_entry(entry_id: int, updated: TimesheetEntryUpdate):
    try:
        existing = supabase.table("timesheets").select("*").eq("id", entry_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Timesheet entry not found")
        
        data_to_update = {k: v for k, v in updated.dict().items() if v is not None}
        data_to_update["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("timesheets").update(data_to_update).eq("id", entry_id).execute()
        
        if response.data:
            result = response.data[0]
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating timesheet entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating timesheet entry: {str(e)}")

@router.delete("/timesheets/{entry_id}")
async def delete_timesheet_entry(entry_id: int):
    try:
        existing = supabase.table("timesheets").select("*").eq("id", entry_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Timesheet entry not found")
        
        supabase.table("timesheets").delete().eq("id", entry_id).execute()
        return {"success": True, "message": "Timesheet entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting timesheet entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting timesheet entry: {str(e)}")

# Holidays Endpoints
@router.get("/holidays")
async def get_holidays(
    start_date: Optional[date] = Query(None, alias="start_date"),
    end_date: Optional[date] = Query(None, alias="end_date")
):
    try:
        query = supabase.table("holidays").select("*")
        
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
            
        response = query.order("date").execute()
        
        records = response.data or []
        for record in records:
            convert_dates_to_iso(record)
            
        return records
        
    except Exception as e:
        logger.error(f"Error fetching holidays: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching holidays: {str(e)}")

@router.post("/holidays")
async def create_holiday(holiday: HolidayCreate):
    try:
        data_to_insert = holiday.dict()
        
        if data_to_insert.get('date'):
            data_to_insert['date'] = data_to_insert['date'].isoformat()
            
        data_to_insert["created_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("holidays").insert(data_to_insert).execute()
        
        if response.data:
            result = response.data[0]
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to create holiday")
            
    except Exception as e:
        logger.error(f"Error creating holiday: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating holiday: {str(e)}")

@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: int):
    try:
        existing = supabase.table("holidays").select("*").eq("id", holiday_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Holiday not found")
        
        supabase.table("holidays").delete().eq("id", holiday_id).execute()
        return {"success": True, "message": "Holiday deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting holiday: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting holiday: {str(e)}")

# Leave Days Endpoints
@router.get("/leave-days")
async def get_leave_days(
    employee_id: Optional[int] = Query(None, alias="employee_id"),
    start_date: Optional[date] = Query(None, alias="start_date"),
    end_date: Optional[date] = Query(None, alias="end_date")
):
    try:
        query = supabase.table("leave_days").select("*, employees(*)")
        
        if employee_id:
            query = query.eq("employee_id", employee_id)
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
            
        response = query.order("date", desc=True).execute()
        
        records = response.data or []
        for record in records:
            convert_dates_to_iso(record)
            if record.get('employees'):
                convert_dates_to_iso(record['employees'])
            
        return records
        
    except Exception as e:
        logger.error(f"Error fetching leave days: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching leave days: {str(e)}")

@router.post("/leave-days")
async def create_leave_day(leave_day: LeaveDayCreate):
    try:
        data_to_insert = leave_day.dict()
        
        if data_to_insert.get('date'):
            data_to_insert['date'] = data_to_insert['date'].isoformat()
            
        data_to_insert["created_at"] = datetime.utcnow().isoformat()
        data_to_insert["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("leave_days").insert(data_to_insert).execute()
        
        if response.data:
            result = response.data[0]
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to create leave day")
            
    except Exception as e:
        logger.error(f"Error creating leave day: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating leave day: {str(e)}")

@router.delete("/leave-days/{leave_day_id}")
async def delete_leave_day(leave_day_id: int):
    try:
        existing = supabase.table("leave_days").select("*").eq("id", leave_day_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Leave day not found")
        
        supabase.table("leave_days").delete().eq("id", leave_day_id).execute()
        return {"success": True, "message": "Leave day deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting leave day: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting leave day: {str(e)}")

# Statistics Endpoints
@router.get("/stats/monthly-summary")
async def get_monthly_summary(
    year: int = Query(..., alias="year"),
    month: int = Query(..., alias="month"),
    department: Optional[str] = Query(None, alias="department")
):
    try:
        # Calculate date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Get all timesheets for the month
        timesheets_query = supabase.table("timesheets").select("*, employees(*)")
        timesheets_query = timesheets_query.gte("date", start_date.isoformat())
        timesheets_query = timesheets_query.lt("date", end_date.isoformat())
        
        if department and department != 'all':
            employee_query = supabase.table("employees").select("id").eq("department", department).execute()
            employee_ids = [emp['id'] for emp in employee_query.data] if employee_query.data else []
            if employee_ids:
                timesheets_query = timesheets_query.in_("employee_id", employee_ids)
        
        timesheets_response = timesheets_query.execute()
        timesheets = timesheets_response.data or []
        
        # Get all employees
        employees_query = supabase.table("employees").select("*")
        if department and department != 'all':
            employees_query = employees_query.eq("department", department)
        employees_response = employees_query.execute()
        employees = employees_response.data or []
        
        # Calculate totals
        total_regular = 0
        total_overtime = 0
        total_holiday_overtime = 0
        total_hours = 0
        total_pay = 0
        total_days_worked = 0
        
        employee_totals = {}
        
        for employee in employees:
            employee_totals[employee['id']] = {
                'regular': 0,
                'overtime': 0,
                'holiday_overtime': 0,
                'total_hours': 0,
                'days_worked': 0,
                'total_pay': 0,
                'employee': employee
            }
        
        for timesheet in timesheets:
            employee_id = timesheet['employee_id']
            if employee_id in employee_totals:
                employee_totals[employee_id]['regular'] += timesheet.get('regular_hours', 0) or 0
                employee_totals[employee_id]['overtime'] += timesheet.get('overtime_hours', 0) or 0
                employee_totals[employee_id]['holiday_overtime'] += timesheet.get('holiday_overtime_hours', 0) or 0
                employee_totals[employee_id]['total_hours'] += timesheet.get('total_hours', 0) or 0
                if timesheet.get('total_hours', 0) > 0:
                    employee_totals[employee_id]['days_worked'] += 1
        
        # Calculate pay for each employee
        for employee_id, totals in employee_totals.items():
            employee_rate = totals['employee']['rate']
            totals['total_pay'] = (
                totals['regular'] * employee_rate +
                totals['overtime'] * employee_rate * 1.5 +
                totals['holiday_overtime'] * employee_rate * 2.0
            )
            
            total_regular += totals['regular']
            total_overtime += totals['overtime']
            total_holiday_overtime += totals['holiday_overtime']
            total_hours += totals['total_hours']
            total_pay += totals['total_pay']
            total_days_worked += totals['days_worked']
        
        return {
            "total_regular": round(total_regular, 2),
            "total_overtime": round(total_overtime, 2),
            "total_holiday_overtime": round(total_holiday_overtime, 2),
            "total_hours": round(total_hours, 2),
            "total_pay": round(total_pay, 2),
            "total_days_worked": total_days_worked,
            "employee_breakdown": employee_totals,
            "month": month,
            "year": year,
            "department": department
        }
        
    except Exception as e:
        logger.error(f"Error fetching monthly summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching monthly summary: {str(e)}")

@router.get("/stats/employee-summary/{employee_id}")
async def get_employee_summary(
    employee_id: int,
    year: int = Query(..., alias="year"),
    month: int = Query(..., alias="month")
):
    try:
        # Calculate date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Get employee details
        employee_response = supabase.table("employees").select("*").eq("id", employee_id).execute()
        if not employee_response.data:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        employee = employee_response.data[0]
        
        # Get timesheets for the month
        timesheets_response = supabase.table("timesheets").select("*")
        timesheets_response = timesheets_response.eq("employee_id", employee_id)
        timesheets_response = timesheets_response.gte("date", start_date.isoformat())
        timesheets_response = timesheets_response.lt("date", end_date.isoformat())
        timesheets_response = timesheets_response.execute()
        
        timesheets = timesheets_response.data or []
        
        # Calculate totals
        total_regular = 0
        total_overtime = 0
        total_holiday_overtime = 0
        total_hours = 0
        total_days_worked = 0
        
        daily_breakdown = []
        
        for timesheet in timesheets:
            total_regular += timesheet.get('regular_hours', 0) or 0
            total_overtime += timesheet.get('overtime_hours', 0) or 0
            total_holiday_overtime += timesheet.get('holiday_overtime_hours', 0) or 0
            total_hours += timesheet.get('total_hours', 0) or 0
            if timesheet.get('total_hours', 0) > 0:
                total_days_worked += 1
            
            daily_breakdown.append({
                'date': timesheet['date'],
                'regular_hours': timesheet.get('regular_hours', 0) or 0,
                'overtime_hours': timesheet.get('overtime_hours', 0) or 0,
                'holiday_overtime_hours': timesheet.get('holiday_overtime_hours', 0) or 0,
                'total_hours': timesheet.get('total_hours', 0) or 0,
                'status': timesheet.get('status', 'work')
            })
        
        total_pay = (
            total_regular * employee['rate'] +
            total_overtime * employee['rate'] * 1.5 +
            total_holiday_overtime * employee['rate'] * 2.0
        )
        
        return {
            "employee": employee,
            "total_regular": round(total_regular, 2),
            "total_overtime": round(total_overtime, 2),
            "total_holiday_overtime": round(total_holiday_overtime, 2),
            "total_hours": round(total_hours, 2),
            "total_pay": round(total_pay, 2),
            "total_days_worked": total_days_worked,
            "daily_breakdown": daily_breakdown,
            "month": month,
            "year": year
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching employee summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching employee summary: {str(e)}")

@router.get("/stats/overview")
async def get_system_overview():
    try:
        # Get counts
        employees_count = supabase.table("employees").select("id", count="exact").execute()
        timesheets_count = supabase.table("timesheets").select("id", count="exact").execute()
        holidays_count = supabase.table("holidays").select("id", count="exact").execute()
        
        # Get current month totals
        today = date.today()
        monthly_summary = await get_monthly_summary(year=today.year, month=today.month)
        
        return {
            "total_employees": len(employees_count.data) if employees_count.data else 0,
            "total_timesheets": len(timesheets_count.data) if timesheets_count.data else 0,
            "total_holidays": len(holidays_count.data) if holidays_count.data else 0,
            "current_month": monthly_summary
        }
        
    except Exception as e:
        logger.error(f"Error fetching system overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching system overview: {str(e)}")