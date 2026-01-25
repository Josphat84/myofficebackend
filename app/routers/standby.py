# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
import time

app = FastAPI()

# CORS setup - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# In-memory storage
employees_db = []
standby_db = []
next_employee_id = 1
next_schedule_id = 1

# Models
class EmployeeBase(BaseModel):
    name: str
    position: str
    designation: Optional[str] = None
    department: str
    contact: str
    email: str
    location: str
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    pass

class Employee(EmployeeBase):
    id: int
    created_at: str
    updated_at: str

class StandbyBase(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    residence: str
    status: str = "scheduled"
    priority: str = "medium"
    notes: Optional[str] = None
    notified: bool = False

class StandbyCreate(StandbyBase):
    pass

class Standby(StandbyBase):
    id: int
    duration_days: Optional[int] = None
    created_at: str
    updated_at: str

class StandbyWithEmployee(Standby):
    employee: Optional[Employee] = None

# Helper functions
def get_current_timestamp():
    return datetime.now().isoformat()

def calculate_duration(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1

def find_employee(employee_id: int) -> Optional[Employee]:
    for emp in employees_db:
        if emp.id == employee_id:
            return emp
    return None

def find_schedule(schedule_id: int) -> Optional[Standby]:
    for schedule in standby_db:
        if schedule.id == schedule_id:
            return schedule
    return None

# Root endpoint - Should return 200 OK
@app.get("/")
def root():
    return {
        "message": "Standby Management API is running",
        "version": "1.0.0",
        "endpoints": {
            "employees": "/api/employees",
            "standby": "/api/standby",
            "health": "/health"
        }
    }

# Test endpoint to verify API is accessible
@app.get("/test")
def test_endpoint():
    return {"status": "ok", "message": "API is working"}

# Employee endpoints
@app.get("/api/employees")
def get_employees():
    """Get all employees"""
    return employees_db

@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int):
    """Get employee by ID"""
    employee = find_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@app.post("/api/employees")
def create_employee(employee: EmployeeCreate):
    """Create a new employee"""
    global next_employee_id
    timestamp = get_current_timestamp()
    
    new_employee = Employee(
        id=next_employee_id,
        created_at=timestamp,
        updated_at=timestamp,
        **employee.dict()
    )
    
    employees_db.append(new_employee)
    next_employee_id += 1
    
    return new_employee

@app.put("/api/employees/{employee_id}")
def update_employee(employee_id: int, employee_update: EmployeeCreate):
    """Update an employee"""
    for i, emp in enumerate(employees_db):
        if emp.id == employee_id:
            # Update employee
            updated_employee = Employee(
                id=employee_id,
                created_at=emp.created_at,
                updated_at=get_current_timestamp(),
                **employee_update.dict()
            )
            employees_db[i] = updated_employee
            return updated_employee
    
    raise HTTPException(status_code=404, detail="Employee not found")

@app.delete("/api/employees/{employee_id}")
def delete_employee(employee_id: int):
    """Delete an employee"""
    for i, emp in enumerate(employees_db):
        if emp.id == employee_id:
            employees_db.pop(i)
            # Also delete associated standby schedules
            global standby_db
            standby_db = [s for s in standby_db if s.employee_id != employee_id]
            return {"message": "Employee deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Employee not found")

# Standby endpoints
@app.get("/api/standby")
def get_standby_schedules():
    """Get all standby schedules with employee data"""
    schedules_with_employee = []
    
    for schedule in standby_db:
        schedule_dict = schedule.dict()
        employee = find_employee(schedule.employee_id)
        schedule_dict["employee"] = employee
        schedules_with_employee.append(StandbyWithEmployee(**schedule_dict))
    
    return schedules_with_employee

@app.get("/api/standby/{schedule_id}")
def get_standby_schedule(schedule_id: int):
    """Get standby schedule by ID"""
    schedule = find_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule_dict = schedule.dict()
    employee = find_employee(schedule.employee_id)
    schedule_dict["employee"] = employee
    
    return StandbyWithEmployee(**schedule_dict)

@app.post("/api/standby")
def create_standby_schedule(schedule: StandbyCreate):
    """Create a new standby schedule"""
    # Check if employee exists
    employee = find_employee(schedule.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    global next_schedule_id
    timestamp = get_current_timestamp()
    
    # Calculate duration
    duration = calculate_duration(schedule.start_date, schedule.end_date)
    
    new_schedule = Standby(
        id=next_schedule_id,
        duration_days=duration,
        created_at=timestamp,
        updated_at=timestamp,
        **schedule.dict()
    )
    
    standby_db.append(new_schedule)
    next_schedule_id += 1
    
    return new_schedule

# Alternative endpoint for frontend compatibility
@app.post("/api/standby/create")
def create_standby_schedule_alt(schedule: StandbyCreate):
    """Alternative endpoint for creating standby schedules"""
    return create_standby_schedule(schedule)

@app.put("/api/standby/{schedule_id}")
def update_standby_schedule(schedule_id: int, schedule_update: StandbyCreate):
    """Update a standby schedule"""
    for i, schedule in enumerate(standby_db):
        if schedule.id == schedule_id:
            # Check if employee exists
            employee = find_employee(schedule_update.employee_id)
            if not employee:
                raise HTTPException(status_code=404, detail="Employee not found")
            
            # Calculate duration
            duration = calculate_duration(schedule_update.start_date, schedule_update.end_date)
            
            updated_schedule = Standby(
                id=schedule_id,
                duration_days=duration,
                created_at=schedule.created_at,
                updated_at=get_current_timestamp(),
                **schedule_update.dict()
            )
            
            standby_db[i] = updated_schedule
            return updated_schedule
    
    raise HTTPException(status_code=404, detail="Schedule not found")

@app.patch("/api/standby/{schedule_id}")
def patch_standby_schedule(
    schedule_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    notified: Optional[bool] = None
):
    """Partially update a standby schedule"""
    schedule = find_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule_dict = schedule.dict()
    
    if status is not None:
        schedule_dict["status"] = status
    
    if priority is not None:
        schedule_dict["priority"] = priority
    
    if notified is not None:
        schedule_dict["notified"] = notified
    
    schedule_dict["updated_at"] = get_current_timestamp()
    
    # Update in database
    for i, sched in enumerate(standby_db):
        if sched.id == schedule_id:
            updated_schedule = Standby(**schedule_dict)
            standby_db[i] = updated_schedule
            return updated_schedule
    
    return schedule_dict

@app.delete("/api/standby/{schedule_id}")
def delete_standby_schedule(schedule_id: int):
    """Delete a standby schedule"""
    for i, schedule in enumerate(standby_db):
        if schedule.id == schedule_id:
            standby_db.pop(i)
            return {"message": "Schedule deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Schedule not found")

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Standby Management API is running",
        "timestamp": get_current_timestamp(),
        "counts": {
            "employees": len(employees_db),
            "standby_schedules": len(standby_db)
        }
    }

# Clear all data (for testing/reset)
@app.delete("/api/clear")
def clear_all_data():
    """Clear all data (for testing purposes)"""
    global employees_db, standby_db, next_employee_id, next_schedule_id
    employees_db = []
    standby_db = []
    next_employee_id = 1
    next_schedule_id = 1
    return {"message": "All data cleared successfully"}# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
import time

app = FastAPI()

# CORS setup - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# In-memory storage
employees_db = []
standby_db = []
next_employee_id = 1
next_schedule_id = 1

# Models
class EmployeeBase(BaseModel):
    name: str
    position: str
    designation: Optional[str] = None
    department: str
    contact: str
    email: str
    location: str
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    pass

class Employee(EmployeeBase):
    id: int
    created_at: str
    updated_at: str

class StandbyBase(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    residence: str
    status: str = "scheduled"
    priority: str = "medium"
    notes: Optional[str] = None
    notified: bool = False

class StandbyCreate(StandbyBase):
    pass

class Standby(StandbyBase):
    id: int
    duration_days: Optional[int] = None
    created_at: str
    updated_at: str

class StandbyWithEmployee(Standby):
    employee: Optional[Employee] = None

# Helper functions
def get_current_timestamp():
    return datetime.now().isoformat()

def calculate_duration(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1

def find_employee(employee_id: int) -> Optional[Employee]:
    for emp in employees_db:
        if emp.id == employee_id:
            return emp
    return None

def find_schedule(schedule_id: int) -> Optional[Standby]:
    for schedule in standby_db:
        if schedule.id == schedule_id:
            return schedule
    return None

# Root endpoint - Should return 200 OK
@app.get("/")
def root():
    return {
        "message": "Standby Management API is running",
        "version": "1.0.0",
        "endpoints": {
            "employees": "/api/employees",
            "standby": "/api/standby",
            "health": "/health"
        }
    }

# Test endpoint to verify API is accessible
@app.get("/test")
def test_endpoint():
    return {"status": "ok", "message": "API is working"}

# Employee endpoints
@app.get("/api/employees")
def get_employees():
    """Get all employees"""
    return employees_db

@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int):
    """Get employee by ID"""
    employee = find_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@app.post("/api/employees")
def create_employee(employee: EmployeeCreate):
    """Create a new employee"""
    global next_employee_id
    timestamp = get_current_timestamp()
    
    new_employee = Employee(
        id=next_employee_id,
        created_at=timestamp,
        updated_at=timestamp,
        **employee.dict()
    )
    
    employees_db.append(new_employee)
    next_employee_id += 1
    
    return new_employee

@app.put("/api/employees/{employee_id}")
def update_employee(employee_id: int, employee_update: EmployeeCreate):
    """Update an employee"""
    for i, emp in enumerate(employees_db):
        if emp.id == employee_id:
            # Update employee
            updated_employee = Employee(
                id=employee_id,
                created_at=emp.created_at,
                updated_at=get_current_timestamp(),
                **employee_update.dict()
            )
            employees_db[i] = updated_employee
            return updated_employee
    
    raise HTTPException(status_code=404, detail="Employee not found")

@app.delete("/api/employees/{employee_id}")
def delete_employee(employee_id: int):
    """Delete an employee"""
    for i, emp in enumerate(employees_db):
        if emp.id == employee_id:
            employees_db.pop(i)
            # Also delete associated standby schedules
            global standby_db
            standby_db = [s for s in standby_db if s.employee_id != employee_id]
            return {"message": "Employee deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Employee not found")

# Standby endpoints
@app.get("/api/standby")
def get_standby_schedules():
    """Get all standby schedules with employee data"""
    schedules_with_employee = []
    
    for schedule in standby_db:
        schedule_dict = schedule.dict()
        employee = find_employee(schedule.employee_id)
        schedule_dict["employee"] = employee
        schedules_with_employee.append(StandbyWithEmployee(**schedule_dict))
    
    return schedules_with_employee

@app.get("/api/standby/{schedule_id}")
def get_standby_schedule(schedule_id: int):
    """Get standby schedule by ID"""
    schedule = find_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule_dict = schedule.dict()
    employee = find_employee(schedule.employee_id)
    schedule_dict["employee"] = employee
    
    return StandbyWithEmployee(**schedule_dict)

@app.post("/api/standby")
def create_standby_schedule(schedule: StandbyCreate):
    """Create a new standby schedule"""
    # Check if employee exists
    employee = find_employee(schedule.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    global next_schedule_id
    timestamp = get_current_timestamp()
    
    # Calculate duration
    duration = calculate_duration(schedule.start_date, schedule.end_date)
    
    new_schedule = Standby(
        id=next_schedule_id,
        duration_days=duration,
        created_at=timestamp,
        updated_at=timestamp,
        **schedule.dict()
    )
    
    standby_db.append(new_schedule)
    next_schedule_id += 1
    
    return new_schedule

# Alternative endpoint for frontend compatibility
@app.post("/api/standby/create")
def create_standby_schedule_alt(schedule: StandbyCreate):
    """Alternative endpoint for creating standby schedules"""
    return create_standby_schedule(schedule)

@app.put("/api/standby/{schedule_id}")
def update_standby_schedule(schedule_id: int, schedule_update: StandbyCreate):
    """Update a standby schedule"""
    for i, schedule in enumerate(standby_db):
        if schedule.id == schedule_id:
            # Check if employee exists
            employee = find_employee(schedule_update.employee_id)
            if not employee:
                raise HTTPException(status_code=404, detail="Employee not found")
            
            # Calculate duration
            duration = calculate_duration(schedule_update.start_date, schedule_update.end_date)
            
            updated_schedule = Standby(
                id=schedule_id,
                duration_days=duration,
                created_at=schedule.created_at,
                updated_at=get_current_timestamp(),
                **schedule_update.dict()
            )
            
            standby_db[i] = updated_schedule
            return updated_schedule
    
    raise HTTPException(status_code=404, detail="Schedule not found")

@app.patch("/api/standby/{schedule_id}")
def patch_standby_schedule(
    schedule_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    notified: Optional[bool] = None
):
    """Partially update a standby schedule"""
    schedule = find_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule_dict = schedule.dict()
    
    if status is not None:
        schedule_dict["status"] = status
    
    if priority is not None:
        schedule_dict["priority"] = priority
    
    if notified is not None:
        schedule_dict["notified"] = notified
    
    schedule_dict["updated_at"] = get_current_timestamp()
    
    # Update in database
    for i, sched in enumerate(standby_db):
        if sched.id == schedule_id:
            updated_schedule = Standby(**schedule_dict)
            standby_db[i] = updated_schedule
            return updated_schedule
    
    return schedule_dict

@app.delete("/api/standby/{schedule_id}")
def delete_standby_schedule(schedule_id: int):
    """Delete a standby schedule"""
    for i, schedule in enumerate(standby_db):
        if schedule.id == schedule_id:
            standby_db.pop(i)
            return {"message": "Schedule deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Schedule not found")

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Standby Management API is running",
        "timestamp": get_current_timestamp(),
        "counts": {
            "employees": len(employees_db),
            "standby_schedules": len(standby_db)
        }
    }

# Clear all data (for testing/reset)
@app.delete("/api/clear")
def clear_all_data():
    """Clear all data (for testing purposes)"""
    global employees_db, standby_db, next_employee_id, next_schedule_id
    employees_db = []
    standby_db = []
    next_employee_id = 1
    next_schedule_id = 1
    return {"message": "All data cleared successfully"}