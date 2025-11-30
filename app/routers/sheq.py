from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, date
from app.supabase_client import supabase
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()  # ✅ FIXED: Removed prefix="/api/sheq"

# Custom JSON encoder to handle date objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

# Pydantic Models
class SHEQReportCreate(BaseModel):
    report_type: str = Field(..., min_length=1)  # hazard, near_miss, incident, pto
    employee_name: str = Field(..., min_length=1)
    employee_id: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    position: Optional[str] = None
    location: str = Field(..., min_length=1)
    date_reported: date
    time_reported: Optional[str] = None
    priority: str = Field(default="medium")
    status: str = Field(default="open")
    
    # Hazard Report Fields
    hazard_description: Optional[str] = None
    risk_assessment: Optional[str] = None
    suggested_improvements: Optional[str] = None
    requirements: Optional[str] = None
    
    # Near Miss Fields
    near_miss_description: Optional[str] = None
    potential_severity: Optional[str] = None
    immediate_causes: Optional[str] = None
    root_causes: Optional[str] = None
    
    # Incident Fields
    incident_description: Optional[str] = None
    incident_type: Optional[str] = None
    injury_type: Optional[str] = None
    property_damage: Optional[str] = None
    environmental_impact: Optional[str] = None
    immediate_actions: Optional[str] = None
    
    # PTO Fields
    supervisor_name: Optional[str] = None
    supervisor_id: Optional[str] = None
    employee_observed: Optional[str] = None
    employee_observed_id: Optional[str] = None
    task_observed: Optional[str] = None
    safe_behaviors: Optional[str] = None
    at_risk_behaviors: Optional[str] = None
    recommendations: Optional[str] = None
    
    # Common Fields
    description: Optional[str] = None
    corrective_actions: Optional[str] = None
    responsible_person: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    completion_date: Optional[date] = None
    notes: Optional[str] = None
    reported_by: Optional[str] = None
    mine_section: Optional[str] = None

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

class SHEQReportUpdate(BaseModel):
    employee_name: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None
    date_reported: Optional[date] = None
    time_reported: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    
    # Hazard Report Fields
    hazard_description: Optional[str] = None
    risk_assessment: Optional[str] = None
    suggested_improvements: Optional[str] = None
    requirements: Optional[str] = None
    
    # Near Miss Fields
    near_miss_description: Optional[str] = None
    potential_severity: Optional[str] = None
    immediate_causes: Optional[str] = None
    root_causes: Optional[str] = None
    
    # Incident Fields
    incident_description: Optional[str] = None
    incident_type: Optional[str] = None
    injury_type: Optional[str] = None
    property_damage: Optional[str] = None
    environmental_impact: Optional[str] = None
    immediate_actions: Optional[str] = None
    
    # PTO Fields
    supervisor_name: Optional[str] = None
    supervisor_id: Optional[str] = None
    employee_observed: Optional[str] = None
    employee_observed_id: Optional[str] = None
    task_observed: Optional[str] = None
    safe_behaviors: Optional[str] = None
    at_risk_behaviors: Optional[str] = None
    recommendations: Optional[str] = None
    
    # Common Fields
    description: Optional[str] = None
    corrective_actions: Optional[str] = None
    responsible_person: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    completion_date: Optional[date] = None
    notes: Optional[str] = None
    reported_by: Optional[str] = None
    mine_section: Optional[str] = None

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

# SHEQ Reports Endpoints
@router.get("")  # ✅ FIXED: Was "/reports"
async def get_sheq_reports(
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    employee_id: Optional[str] = None,
    search: Optional[str] = None
):
    try:
        query = supabase.table("sheq_reports").select("*")
        
        if report_type and report_type != 'all':
            query = query.eq("report_type", report_type)
        if status and status != 'all':
            query = query.eq("status", status)
        if priority and priority != 'all':
            query = query.eq("priority", priority)
        if department and department != 'all':
            query = query.eq("department", department)
        if location and location != 'all':
            query = query.eq("location", location)
        if employee_id and employee_id != 'all':
            query = query.eq("employee_id", employee_id)
        if search:
            query = query.or_(f"employee_name.ilike.%{search}%,employee_id.ilike.%{search}%,location.ilike.%{search}%,description.ilike.%{search}%")
            
        response = query.order("created_at", desc=True).execute()
        
        # Convert dates to ISO format for JSON serialization
        records = response.data or []
        for record in records:
            convert_dates_to_iso(record)
            
        return records
        
    except Exception as e:
        logger.error(f"Error fetching SHEQ reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching SHEQ reports: {str(e)}")

@router.post("")  # ✅ FIXED: Was "/reports"
async def create_sheq_report(report: SHEQReportCreate):
    try:
        # Convert Pydantic model to dict and handle date serialization
        data_to_insert = report.dict()
        
        # Ensure dates are properly formatted for database
        date_fields = ['date_reported', 'due_date', 'completion_date']
        for field in date_fields:
            if data_to_insert.get(field):
                data_to_insert[field] = data_to_insert[field].isoformat()
            
        data_to_insert["created_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("sheq_reports").insert(data_to_insert).execute()
        
        if response.data:
            # Convert dates to ISO format for JSON response
            result = response.data[0]
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to create SHEQ report")
            
    except Exception as e:
        logger.error(f"Error creating SHEQ report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating SHEQ report: {str(e)}")

@router.get("/{report_id}")  # ✅ FIXED: Was "/reports/{report_id}"
async def get_sheq_report(report_id: int):
    try:
        response = supabase.table("sheq_reports").select("*").eq("id", report_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="SHEQ report not found")
        
        result = response.data[0]
        convert_dates_to_iso(result)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching SHEQ report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching SHEQ report: {str(e)}")

@router.patch("/{report_id}")  # ✅ FIXED: Was "/reports/{report_id}" and changed PUT to PATCH
async def update_sheq_report(report_id: int, updated: SHEQReportUpdate):
    try:
        existing = supabase.table("sheq_reports").select("*").eq("id", report_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="SHEQ report not found")
        
        data_to_update = {k: v for k, v in updated.dict().items() if v is not None}
        
        # Convert dates to ISO format for database
        date_fields = ['date_reported', 'due_date', 'completion_date']
        for field in date_fields:
            if data_to_update.get(field):
                data_to_update[field] = data_to_update[field].isoformat()
            
        data_to_update["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("sheq_reports").update(data_to_update).eq("id", report_id).execute()
        
        if response.data:
            result = response.data[0]
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating SHEQ report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating SHEQ report: {str(e)}")

@router.delete("/{report_id}")  # ✅ FIXED: Was "/reports/{report_id}"
async def delete_sheq_report(report_id: int):
    try:
        existing = supabase.table("sheq_reports").select("*").eq("id", report_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="SHEQ report not found")
        
        supabase.table("sheq_reports").delete().eq("id", report_id).execute()
        return {"success": True, "message": "SHEQ report deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting SHEQ report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting SHEQ report: {str(e)}")

@router.get("/employee/{employee_id}")  # ✅ FIXED: Was "/reports/employee/{employee_id}"
async def get_employee_sheq_reports(employee_id: str):
    try:
        response = supabase.table("sheq_reports").select("*").eq("employee_id", employee_id).order("date_reported", desc=True).execute()
        
        # Convert dates to ISO format for JSON serialization
        records = response.data or []
        for record in records:
            convert_dates_to_iso(record)
            
        return records
        
    except Exception as e:
        logger.error(f"Error fetching employee SHEQ reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching employee SHEQ reports: {str(e)}")

# Statistics Endpoint
@router.get("/stats/summary")  # ✅ FIXED: Was "/stats"
async def get_sheq_stats():
    try:
        # Get total reports count
        reports_response = supabase.table("sheq_reports").select("id", count="exact").execute()
        total_reports = len(reports_response.data) if reports_response.data else 0
        
        # Get reports by status
        status_response = supabase.table("sheq_reports").select("status").execute()
        status_counts = {}
        if status_response.data:
            for record in status_response.data:
                status = record.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
        
        # Get reports by type
        type_response = supabase.table("sheq_reports").select("report_type").execute()
        type_counts = {}
        if type_response.data:
            for record in type_response.data:
                report_type = record.get('report_type', 'unknown')
                type_counts[report_type] = type_counts.get(report_type, 0) + 1
        
        # Get reports by priority
        priority_response = supabase.table("sheq_reports").select("priority").execute()
        priority_counts = {}
        if priority_response.data:
            for record in priority_response.data:
                priority = record.get('priority', 'unknown')
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Count overdue actions
        today = date.today()
        reports_all = supabase.table("sheq_reports").select("due_date, status").execute()
        overdue = 0
        open_reports = 0
        
        if reports_all.data:
            for record in reports_all.data:
                due_date_str = record.get('due_date')
                status = record.get('status', 'open')
                
                if status in ['open', 'in_progress']:
                    open_reports += 1
                
                if due_date_str and status in ['open', 'in_progress']:
                    try:
                        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                        if due_date < today:
                            overdue += 1
                    except (ValueError, TypeError):
                        # Handle invalid date formats
                        continue
        
        # Get unique employees count
        employees_response = supabase.table("sheq_reports").select("employee_id").execute()
        unique_employees = len(set(record['employee_id'] for record in employees_response.data)) if employees_response.data else 0
        
        return {
            "total_reports": total_reports,
            "open_reports": open_reports,
            "overdue_actions": overdue,
            "unique_employees": unique_employees,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "priority_breakdown": priority_counts
        }
        
    except Exception as e:
        logger.error(f"Error fetching SHEQ stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching SHEQ stats: {str(e)}")

# Employees Endpoint for autocomplete
@router.get("/employees")  # ✅ This was already correct
async def get_employees():
    try:
        # Get unique employees from SHEQ reports
        response = supabase.table("sheq_reports").select("employee_id, employee_name, department, position").execute()
        
        employees_map = {}
        if response.data:
            for record in response.data:
                employee_id = record.get('employee_id')
                if employee_id and employee_id not in employees_map:
                    employees_map[employee_id] = {
                        'employee_id': employee_id,
                        'employee_name': record.get('employee_name'),
                        'department': record.get('department'),
                        'position': record.get('position')
                    }
        
        return list(employees_map.values())
        
    except Exception as e:
        logger.error(f"Error fetching employees: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching employees: {str(e)}")
