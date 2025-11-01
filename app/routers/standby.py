# backend/app/routers/standby.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/standby", tags=["standby"])

# Pydantic models
class StandbyRoster(BaseModel):
    id: str
    title: str
    type: str
    department: str
    primaryContact: str
    secondaryContact: str
    startDate: str
    endDate: str
    status: str
    location: str
    notes: str
    responseTime: str
    createdAt: str
    updatedAt: str

class StandbyRosterCreate(BaseModel):
    title: str
    type: str
    department: str
    primaryContact: str
    secondaryContact: str
    startDate: str
    endDate: str
    location: str
    notes: str
    responseTime: str

class StandbyRosterUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    department: Optional[str] = None
    primaryContact: Optional[str] = None
    secondaryContact: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    responseTime: Optional[str] = None

# Mock database
standby_db = {}

def init_sample_data():
    now = datetime.now()
    sample_rosters = [
        {
            "id": "sb-001",
            "title": "Weekend Emergency Maintenance",
            "type": "Emergency Response",
            "department": "Maintenance",
            "primaryContact": "emp-1",
            "secondaryContact": "emp-2",
            "startDate": (now.replace(day=now.day + 1)).isoformat(),
            "endDate": (now.replace(day=now.day + 3)).isoformat(),
            "status": "active",
            "location": "Main Plant",
            "notes": "Coverage for critical equipment failures and emergency repairs",
            "responseTime": "30 minutes",
            "createdAt": (now.replace(day=now.day - 2)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 1)).isoformat()
        },
        {
            "id": "sb-002",
            "title": "Night Shift Safety Watch",
            "type": "Safety Watch",
            "department": "Safety",
            "primaryContact": "emp-3",
            "secondaryContact": "emp-1",
            "startDate": now.isoformat(),
            "endDate": (now.replace(day=now.day + 7)).isoformat(),
            "status": "active",
            "location": "All Sites",
            "notes": "24/7 safety monitoring and incident response",
            "responseTime": "Immediate",
            "createdAt": (now.replace(day=now.day - 5)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 1)).isoformat()
        },
        {
            "id": "sb-003",
            "title": "IT Infrastructure Support",
            "type": "Technical Support",
            "department": "IT",
            "primaryContact": "emp-4",
            "secondaryContact": "emp-5",
            "startDate": (now.replace(day=now.day + 2)).isoformat(),
            "endDate": (now.replace(day=now.day + 9)).isoformat(),
            "status": "scheduled",
            "location": "Data Center",
            "notes": "Server and network infrastructure emergency support",
            "responseTime": "15 minutes",
            "createdAt": (now.replace(day=now.day - 3)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 1)).isoformat()
        },
        {
            "id": "sb-004",
            "title": "Medical Emergency Coverage",
            "type": "Medical Standby",
            "department": "Medical",
            "primaryContact": "emp-6",
            "secondaryContact": "emp-3",
            "startDate": (now.replace(day=now.day - 1)).isoformat(),
            "endDate": (now.replace(day=now.day + 6)).isoformat(),
            "status": "active",
            "location": "Medical Center",
            "notes": "Emergency medical response and first aid",
            "responseTime": "5 minutes",
            "createdAt": (now.replace(day=now.day - 7)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 1)).isoformat()
        },
        {
            "id": "sb-005",
            "title": "Operations Control Room",
            "type": "Operations Coverage",
            "department": "Operations",
            "primaryContact": "emp-2",
            "secondaryContact": "emp-1",
            "startDate": (now.replace(day=now.day - 3)).isoformat(),
            "endDate": (now.replace(day=now.day + 2)).isoformat(),
            "status": "completed",
            "location": "Control Room A",
            "notes": "24/7 operations monitoring and coordination",
            "responseTime": "Immediate",
            "createdAt": (now.replace(day=now.day - 10)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 1)).isoformat()
        }
    ]
    
    for roster in sample_rosters:
        standby_db[roster["id"]] = roster

# Initialize sample data
init_sample_data()

@router.get("/rosters", response_model=List[StandbyRoster])
async def get_standby_rosters(
    status: Optional[str] = None,
    department: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None
):
    """Get all standby rosters with optional filtering"""
    rosters = list(standby_db.values())
    
    # Apply filters
    if status:
        rosters = [roster for roster in rosters if roster["status"] == status]
    if department:
        rosters = [roster for roster in rosters if roster["department"] == department]
    if type:
        rosters = [roster for roster in rosters if roster["type"] == type]
    if search:
        search_lower = search.lower()
        rosters = [
            roster for roster in rosters 
            if search_lower in roster["title"].lower() 
            or search_lower in roster["department"].lower()
            or search_lower in roster["notes"].lower()
        ]
    
    return rosters

@router.get("/rosters/{roster_id}", response_model=StandbyRoster)
async def get_standby_roster(roster_id: str):
    """Get a specific standby roster by ID"""
    if roster_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby roster not found")
    return standby_db[roster_id]

@router.post("/rosters", response_model=StandbyRoster)
async def create_standby_roster(roster: StandbyRosterCreate):
    """Create a new standby roster"""
    roster_id = f"sb-{len(standby_db) + 1}"
    now = datetime.now().isoformat()
    
    # Set default status based on start date
    start_date = datetime.fromisoformat(roster.startDate.replace('Z', '+00:00'))
    current_time = datetime.now()
    status = "active" if start_date <= current_time else "scheduled"
    
    new_roster = StandbyRoster(
        id=roster_id,
        **roster.dict(),
        status=status,
        createdAt=now,
        updatedAt=now
    )
    
    standby_db[roster_id] = new_roster.dict()
    return new_roster

@router.put("/rosters/{roster_id}", response_model=StandbyRoster)
async def update_standby_roster(roster_id: str, roster_update: StandbyRosterUpdate):
    """Update an existing standby roster"""
    if roster_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby roster not found")
    
    existing_roster = standby_db[roster_id]
    update_data = roster_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        existing_roster[field] = value
    
    # Auto-update status based on dates if startDate or endDate changed
    if 'startDate' in update_data or 'endDate' in update_data:
        start_date = datetime.fromisoformat(existing_roster['startDate'].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(existing_roster['endDate'].replace('Z', '+00:00'))
        current_time = datetime.now()
        
        if current_time < start_date:
            existing_roster['status'] = 'scheduled'
        elif start_date <= current_time <= end_date:
            existing_roster['status'] = 'active'
        else:
            existing_roster['status'] = 'completed'
    
    existing_roster['updatedAt'] = datetime.now().isoformat()
    standby_db[roster_id] = existing_roster
    
    return existing_roster

@router.delete("/rosters/{roster_id}")
async def delete_standby_roster(roster_id: str):
    """Delete a standby roster"""
    if roster_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby roster not found")
    
    del standby_db[roster_id]
    return {"message": "Standby roster deleted successfully"}

@router.post("/rosters/{roster_id}/activate")
async def activate_roster(roster_id: str):
    """Activate a standby roster"""
    if roster_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby roster not found")
    
    roster = standby_db[roster_id]
    roster['status'] = 'active'
    roster['updatedAt'] = datetime.now().isoformat()
    
    standby_db[roster_id] = roster
    return {"message": "Roster activated", "roster": roster}

@router.post("/rosters/{roster_id}/complete")
async def complete_roster(roster_id: str):
    """Mark a standby roster as completed"""
    if roster_id not in standby_db:
        raise HTTPException(status_code=404, detail="Standby roster not found")
    
    roster = standby_db[roster_id]
    roster['status'] = 'completed'
    roster['updatedAt'] = datetime.now().isoformat()
    
    standby_db[roster_id] = roster
    return {"message": "Roster completed", "roster": roster}

@router.get("/stats")
async def get_standby_stats():
    """Get standby statistics for dashboard"""
    rosters = list(standby_db.values())
    
    total = len(rosters)
    active = len([r for r in rosters if r['status'] == 'active'])
    scheduled = len([r for r in rosters if r['status'] == 'scheduled'])
    completed = len([r for r in rosters if r['status'] == 'completed'])
    
    # Count by department
    departments = {}
    for roster in rosters:
        dept = roster['department']
        departments[dept] = departments.get(dept, 0) + 1
    
    # Count by type
    types = {}
    for roster in rosters:
        roster_type = roster['type']
        types[roster_type] = types.get(roster_type, 0) + 1
    
    return {
        "total": total,
        "active": active,
        "scheduled": scheduled,
        "completed": completed,
        "byDepartment": departments,
        "byType": types
    }

@router.get("/departments")
async def get_departments():
    """Get all departments with standby coverage"""
    departments = set(roster['department'] for roster in standby_db.values())
    return {"departments": sorted(list(departments))}

@router.get("/types")
async def get_roster_types():
    """Get all roster types"""
    types = set(roster['type'] for roster in standby_db.values())
    return {"types": sorted(list(types))}

@router.get("/active")
async def get_active_rosters():
    """Get all currently active standby rosters"""
    now = datetime.now()
    active_rosters = []
    
    for roster in standby_db.values():
        start_date = datetime.fromisoformat(roster['startDate'].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(roster['endDate'].replace('Z', '+00:00'))
        
        if start_date <= now <= end_date and roster['status'] == 'active':
            active_rosters.append(roster)
    
    return {"activeRosters": active_rosters}

@router.get("/upcoming")
async def get_upcoming_rosters(days: int = 7):
    """Get rosters starting within the next specified days"""
    now = datetime.now()
    future_date = now.replace(day=now.day + days)
    
    upcoming_rosters = []
    
    for roster in standby_db.values():
        start_date = datetime.fromisoformat(roster['startDate'].replace('Z', '+00:00'))
        
        if now <= start_date <= future_date and roster['status'] == 'scheduled':
            upcoming_rosters.append(roster)
    
    return {"upcomingRosters": upcoming_rosters}