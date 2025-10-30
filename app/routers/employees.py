# backend/app/routers/employees.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date
from app.supabase_client import supabase

router = APIRouter()

class Employee(BaseModel):
    id: int = Field(..., description="Unique employee ID")
    first_name: str = Field(..., min_length=1, description="First name of the employee")
    last_name: str = Field(..., min_length=1, description="Last name of the employee")
    id_number: str = Field(..., min_length=1, description="National ID or passport number")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Physical address")
    date_of_engagement: date = Field(..., description="Date of employment")
    designation: str = Field(..., min_length=1, description="Job title/position")
    employee_class: Optional[str] = Field(None, description="Employment class (Permanent, Contract, etc.)")
    supervisor: Optional[str] = Field(None, description="Direct supervisor name")
    section: Optional[str] = Field(None, description="Work section")
    department: Optional[str] = Field(None, description="Department")
    grade: Optional[str] = Field(None, description="Job grade")
    qualifications: Optional[List[str]] = Field(default_factory=list, description="List of qualifications")
    drivers_license_class: Optional[str] = Field(None, description="Driver's license class")
    ppe_issue_date: Optional[date] = Field(None, description="PPE issue date")
    offences: Optional[List[str]] = Field(default_factory=list, description="List of offences")
    awards_recognition: Optional[List[str]] = Field(default_factory=list, description="List of awards")
    other_positions: Optional[List[str]] = Field(default_factory=list, description="Other positions held")
    previous_employer: Optional[str] = Field(None, description="Previous employer name")

    class Config:
        json_encoders = {date: lambda v: v.isoformat()}
        schema_extra = {
            "example": {
                "id": 1001,
                "first_name": "John",
                "last_name": "Doe",
                "id_number": "12-345678-A-12",
                "email": "john.doe@company.com",
                "phone": "+263771234567",
                "address": "123 Main Street, Harare",
                "date_of_engagement": "2020-01-15",
                "designation": "Software Engineer",
                "employee_class": "Permanent",
                "supervisor": "Jane Smith",
                "section": "Development",
                "department": "IT",
                "grade": "Senior",
                "qualifications": ["BSc Computer Science", "AWS Certified"],
                "drivers_license_class": "Class 4",
                "ppe_issue_date": "2020-01-20",
                "offences": [],
                "awards_recognition": ["Employee of the Month - March 2023"],
                "other_positions": ["Team Lead"],
                "previous_employer": "Tech Corp Ltd"
            }
        }

    @validator('qualifications', 'offences', 'awards_recognition', 'other_positions', pre=True, always=True)
    def ensure_list(cls, v):
        """Ensure array fields are always lists, never None"""
        if v is None:
            return []
        return v

def process_dates_for_db(data: dict) -> dict:
    """Convert date objects to ISO strings for Supabase"""
    processed_data = data.copy()
    
    if isinstance(processed_data.get('date_of_engagement'), date):
        processed_data['date_of_engagement'] = processed_data['date_of_engagement'].isoformat()
    
    if (processed_data.get('ppe_issue_date') and 
        isinstance(processed_data['ppe_issue_date'], date)):
        processed_data['ppe_issue_date'] = processed_data['ppe_issue_date'].isoformat()
    
    return processed_data

def process_dates_from_db(data: dict) -> dict:
    """Convert ISO date strings back to date objects"""
    processed_data = data.copy()
    
    if processed_data.get('date_of_engagement'):
        try:
            if isinstance(processed_data['date_of_engagement'], str):
                processed_data['date_of_engagement'] = date.fromisoformat(processed_data['date_of_engagement'])
        except (ValueError, TypeError) as e:
            print(f"Error parsing date_of_engagement: {e}")
            processed_data['date_of_engagement'] = None
    
    if processed_data.get('ppe_issue_date'):
        try:
            if isinstance(processed_data['ppe_issue_date'], str):
                processed_data['ppe_issue_date'] = date.fromisoformat(processed_data['ppe_issue_date'])
        except (ValueError, TypeError) as e:
            print(f"Error parsing ppe_issue_date: {e}")
            processed_data['ppe_issue_date'] = None
    
    array_fields = ['qualifications', 'offences', 'awards_recognition', 'other_positions']
    for field in array_fields:
        if processed_data.get(field) is None:
            processed_data[field] = []
        elif not isinstance(processed_data[field], list):
            processed_data[field] = []
    
    return processed_data

def get_supabase_data(response):
    """Helper to extract data from Supabase response"""
    if hasattr(response, 'data'):
        return response.data
    return response

# GET all employees
@router.get("")
@router.get("/")
async def get_employees():
    """Retrieve all employees from the database."""
    try:
        response = supabase.table("employees").select("*").execute()
        data = get_supabase_data(response)
        
        if not data:
            return []
        
        processed_employees = [process_dates_from_db(emp) for emp in data]
        return processed_employees
    except Exception as e:
        print(f"Error fetching employees: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching employees: {str(e)}")

# GET single employee
@router.get("/{employee_id}")
async def get_employee(employee_id: int):
    """Retrieve a specific employee by ID."""
    try:
        response = supabase.table("employees").select("*").eq("id", employee_id).execute()
        data = get_supabase_data(response)
            
        if not data:
            raise HTTPException(status_code=404, detail=f"Employee with ID {employee_id} not found")
        
        employee_data = process_dates_from_db(data[0])
        return employee_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching employee: {str(e)}")

# POST create employee
@router.post("")
@router.post("/")
async def create_employee(employee: Employee):
    """Create a new employee record."""
    try:
        existing_response = supabase.table("employees").select("id").eq("id", employee.id).execute()
        existing_data = get_supabase_data(existing_response)
            
        if existing_data:
            raise HTTPException(
                status_code=400, 
                detail=f"Employee with ID {employee.id} already exists. Please use a different ID."
            )
        
        data_to_insert = employee.dict()
        data_to_insert = process_dates_for_db(data_to_insert)
        
        result = supabase.table("employees").insert(data_to_insert).execute()
        created_data = get_supabase_data(result)
            
        if not created_data:
            raise HTTPException(status_code=500, detail="No data returned after insertion")
            
        created_employee = process_dates_from_db(created_data[0])
        return created_employee
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating employee: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating employee: {str(e)}")

# PUT update employee
@router.put("/{employee_id}")
async def update_employee(employee_id: int, updated: Employee):
    """Update an existing employee record."""
    try:
        existing_response = supabase.table("employees").select("id").eq("id", employee_id).execute()
        existing_data = get_supabase_data(existing_response)
            
        if not existing_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Employee with ID {employee_id} not found"
            )
        
        if updated.id != employee_id:
            raise HTTPException(
                status_code=400,
                detail=f"Employee ID in payload ({updated.id}) does not match URL parameter ({employee_id})"
            )
        
        data_to_update = updated.dict()
        data_to_update = process_dates_for_db(data_to_update)
        
        result = supabase.table("employees").update(data_to_update).eq("id", employee_id).execute()
        updated_data = get_supabase_data(result)
            
        if not updated_data:
            raise HTTPException(status_code=500, detail="No data returned after update")
            
        updated_employee = process_dates_from_db(updated_data[0])
        return updated_employee
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating employee: {str(e)}")

# DELETE employee
@router.delete("/{employee_id}")
async def delete_employee(employee_id: int):
    """Delete an employee record."""
    try:
        existing_response = supabase.table("employees").select("id, first_name, last_name").eq("id", employee_id).execute()
        existing_data = get_supabase_data(existing_response)
            
        if not existing_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Employee with ID {employee_id} not found"
            )
        
        employee_name = f"{existing_data[0].get('first_name', '')} {existing_data[0].get('last_name', '')}".strip() or 'Unknown'
        
        supabase.table("employees").delete().eq("id", employee_id).execute()
            
        return {
            "success": True,
            "detail": f"Employee {employee_id} ({employee_name}) successfully deleted",
            "deleted_id": employee_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting employee: {str(e)}")

# Health check
@router.get("/health/status", tags=["Health"])
async def employees_health():
    """Check if the employees service is operational"""
    try:
        response = supabase.table("employees").select("id").limit(1).execute()
        data = get_supabase_data(response)
        
        return {
            "status": "healthy",
            "service": "employees",
            "database": "connected",
            "message": "Employees service is operational"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Employees service is unhealthy: {str(e)}"
        )