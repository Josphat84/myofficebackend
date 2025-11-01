# backend/app/routers/ppe.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum

router = APIRouter(prefix="/api/ppe", tags=["ppe"])

# Pydantic models
class PPEItem(str, Enum):
    HARD_HAT = "hard_hat"
    SAFETY_GLASSES = "safety_glasses"
    SAFETY_BOOTS = "safety_boots"
    HIGH_VIS_VEST = "high_vis_vest"
    GLOVES = "gloves"
    EAR_PROTECTION = "ear_protection"
    RESPIRATOR = "respirator"
    FALL_PROTECTION = "fall_protection"

class PPEStatus(str, Enum):
    ASSIGNED = "assigned"
    RETURNED = "returned"
    DAMAGED = "damaged"
    LOST = "lost"
    EXPIRED = "expired"

class PPEType(str, Enum):
    ISSUED = "issued"
    RETURNED = "returned"
    INSPECTED = "inspected"
    REPLACED = "replaced"

class PPEIssue(BaseModel):
    id: str
    employeeId: str
    employeeName: str
    ppeItem: PPEItem
    size: str
    issueDate: str
    expiryDate: str
    status: PPEStatus
    condition: str
    lastInspection: Optional[str] = None
    notes: Optional[str] = None
    createdAt: str
    updatedAt: str

class PPEIssueCreate(BaseModel):
    employeeId: str
    ppeItem: PPEItem
    size: str
    issueDate: str
    expiryDate: str
    condition: str
    notes: Optional[str] = None

class PPEIssueUpdate(BaseModel):
    ppeItem: Optional[PPEItem] = None
    size: Optional[str] = None
    issueDate: Optional[str] = None
    expiryDate: Optional[str] = None
    status: Optional[PPEStatus] = None
    condition: Optional[str] = None
    lastInspection: Optional[str] = None
    notes: Optional[str] = None

class PPEInventory(BaseModel):
    ppeItem: PPEItem
    totalStock: int
    assigned: int
    available: int
    lowStock: bool
    reorderLevel: int

class PPEInspection(BaseModel):
    id: str
    ppeIssueId: str
    inspectionDate: str
    inspector: str
    condition: str
    passed: bool
    notes: Optional[str] = None
    nextInspection: str
    createdAt: str

# Mock database
ppe_issues_db = {}
ppe_inventory_db = {}
ppe_inspections_db = {}

def init_sample_data():
    now = datetime.now()
    
    # Sample PPE inventory
    sample_inventory = [
        {
            "ppeItem": "hard_hat",
            "totalStock": 150,
            "assigned": 125,
            "available": 25,
            "lowStock": False,
            "reorderLevel": 20
        },
        {
            "ppeItem": "safety_glasses",
            "totalStock": 200,
            "assigned": 180,
            "available": 20,
            "lowStock": True,
            "reorderLevel": 25
        },
        {
            "ppeItem": "safety_boots",
            "totalStock": 120,
            "assigned": 110,
            "available": 10,
            "lowStock": True,
            "reorderLevel": 15
        },
        {
            "ppeItem": "high_vis_vest",
            "totalStock": 180,
            "assigned": 160,
            "available": 20,
            "lowStock": False,
            "reorderLevel": 20
        },
        {
            "ppeItem": "gloves",
            "totalStock": 300,
            "assigned": 275,
            "available": 25,
            "lowStock": False,
            "reorderLevel": 30
        },
        {
            "ppeItem": "ear_protection",
            "totalStock": 100,
            "assigned": 85,
            "available": 15,
            "lowStock": True,
            "reorderLevel": 15
        },
        {
            "ppeItem": "respirator",
            "totalStock": 80,
            "assigned": 70,
            "available": 10,
            "lowStock": True,
            "reorderLevel": 10
        },
        {
            "ppeItem": "fall_protection",
            "totalStock": 50,
            "assigned": 45,
            "available": 5,
            "lowStock": True,
            "reorderLevel": 5
        }
    ]
    
    for item in sample_inventory:
        ppe_inventory_db[item["ppeItem"]] = item
    
    # Sample PPE issues
    sample_issues = [
        {
            "id": "ppe-001",
            "employeeId": "emp-1",
            "employeeName": "Mike Johnson",
            "ppeItem": "hard_hat",
            "size": "L",
            "issueDate": (now.replace(day=now.day - 30)).isoformat(),
            "expiryDate": (now.replace(day=now.day + 335)).isoformat(),  # 1 year from issue
            "status": "assigned",
            "condition": "good",
            "lastInspection": (now.replace(day=now.day - 7)).isoformat(),
            "notes": "Yellow hard hat with chin strap",
            "createdAt": (now.replace(day=now.day - 30)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 7)).isoformat()
        },
        {
            "id": "ppe-002",
            "employeeId": "emp-1",
            "employeeName": "Mike Johnson",
            "ppeItem": "safety_boots",
            "size": "10",
            "issueDate": (now.replace(day=now.day - 60)).isoformat(),
            "expiryDate": (now.replace(day=now.day + 305)).isoformat(),  # 1 year from issue
            "status": "assigned",
            "condition": "fair",
            "lastInspection": (now.replace(day=now.day - 14)).isoformat(),
            "notes": "Steel-toe boots, needs replacement soon",
            "createdAt": (now.replace(day=now.day - 60)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 14)).isoformat()
        },
        {
            "id": "ppe-003",
            "employeeId": "emp-2",
            "employeeName": "Sarah Chen",
            "ppeItem": "hard_hat",
            "size": "M",
            "issueDate": (now.replace(day=now.day - 15)).isoformat(),
            "expiryDate": (now.replace(day=now.day + 350)).isoformat(),
            "status": "assigned",
            "condition": "excellent",
            "lastInspection": (now.replace(day=now.day - 15)).isoformat(),
            "notes": "White hard hat, new issue",
            "createdAt": (now.replace(day=now.day - 15)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 15)).isoformat()
        },
        {
            "id": "ppe-004",
            "employeeId": "emp-2",
            "employeeName": "Sarah Chen",
            "ppeItem": "high_vis_vest",
            "size": "M",
            "issueDate": (now.replace(day=now.day - 15)).isoformat(),
            "expiryDate": (now.replace(day=now.day + 180)).isoformat(),  # 6 months
            "status": "assigned",
            "condition": "good",
            "lastInspection": (now.replace(day=now.day - 15)).isoformat(),
            "notes": "Orange reflective vest",
            "createdAt": (now.replace(day=now.day - 15)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 15)).isoformat()
        },
        {
            "id": "ppe-005",
            "employeeId": "emp-3",
            "employeeName": "David Rodriguez",
            "ppeItem": "respirator",
            "size": "M",
            "issueDate": (now.replace(day=now.day - 90)).isoformat(),
            "expiryDate": (now.replace(day=now.day - 10)).isoformat(),  # Expired
            "status": "expired",
            "condition": "poor",
            "lastInspection": (now.replace(day=now.day - 30)).isoformat(),
            "notes": "N95 respirator - needs replacement",
            "createdAt": (now.replace(day=now.day - 90)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 10)).isoformat()
        },
        {
            "id": "ppe-006",
            "employeeId": "emp-4",
            "employeeName": "Emily Watson",
            "ppeItem": "fall_protection",
            "size": "L",
            "issueDate": (now.replace(day=now.day - 45)).isoformat(),
            "expiryDate": (now.replace(day=now.day + 320)).isoformat(),
            "status": "assigned",
            "condition": "good",
            "lastInspection": (now.replace(day=now.day - 45)).isoformat(),
            "notes": "Full body harness",
            "createdAt": (now.replace(day=now.day - 45)).isoformat(),
            "updatedAt": (now.replace(day=now.day - 45)).isoformat()
        }
    ]
    
    for issue in sample_issues:
        ppe_issues_db[issue["id"]] = issue
    
    # Sample inspections
    sample_inspections = [
        {
            "id": "insp-001",
            "ppeIssueId": "ppe-001",
            "inspectionDate": (now.replace(day=now.day - 7)).isoformat(),
            "inspector": "safety-officer-1",
            "condition": "good",
            "passed": True,
            "notes": "No visible damage, chin strap intact",
            "nextInspection": (now.replace(day=now.day + 23)).isoformat(),  # Monthly inspection
            "createdAt": (now.replace(day=now.day - 7)).isoformat()
        },
        {
            "id": "insp-002",
            "ppeIssueId": "ppe-002",
            "inspectionDate": (now.replace(day=now.day - 14)).isoformat(),
            "inspector": "safety-officer-1",
            "condition": "fair",
            "passed": True,
            "notes": "Minor wear on soles, monitor for replacement",
            "nextInspection": (now.replace(day=now.day + 16)).isoformat(),
            "createdAt": (now.replace(day=now.day - 14)).isoformat()
        },
        {
            "id": "insp-003",
            "ppeIssueId": "ppe-005",
            "inspectionDate": (now.replace(day=now.day - 30)).isoformat(),
            "inspector": "safety-officer-2",
            "condition": "poor",
            "passed": False,
            "notes": "Straps weakened, replace immediately",
            "nextInspection": (now.replace(day=now.day - 30)).isoformat(),
            "createdAt": (now.replace(day=now.day - 30)).isoformat()
        }
    ]
    
    for inspection in sample_inspections:
        ppe_inspections_db[inspection["id"]] = inspection

# Initialize sample data
init_sample_data()

@router.get("/issues", response_model=List[PPEIssue])
async def get_ppe_issues(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    ppe_item: Optional[str] = None,
    expired: Optional[bool] = None
):
    """Get all PPE issues with optional filtering"""
    issues = list(ppe_issues_db.values())
    
    # Apply filters
    if employee_id:
        issues = [issue for issue in issues if issue["employeeId"] == employee_id]
    if status:
        issues = [issue for issue in issues if issue["status"] == status]
    if ppe_item:
        issues = [issue for issue in issues if issue["ppeItem"] == ppe_item]
    if expired is not None:
        now = datetime.now()
        if expired:
            issues = [issue for issue in issues if datetime.fromisoformat(issue["expiryDate"].replace('Z', '+00:00')) < now]
        else:
            issues = [issue for issue in issues if datetime.fromisoformat(issue["expiryDate"].replace('Z', '+00:00')) >= now]
    
    return issues

@router.get("/issues/{issue_id}", response_model=PPEIssue)
async def get_ppe_issue(issue_id: str):
    """Get a specific PPE issue by ID"""
    if issue_id not in ppe_issues_db:
        raise HTTPException(status_code=404, detail="PPE issue not found")
    return ppe_issues_db[issue_id]

@router.post("/issues", response_model=PPEIssue)
async def create_ppe_issue(issue: PPEIssueCreate):
    """Create a new PPE issue"""
    # Get employee name (in real app, this would come from employees API)
    employee_name = "Unknown Employee"
    # This would typically call your employees API
    # For now, we'll use a simple mapping
    employee_mapping = {
        "emp-1": "Mike Johnson",
        "emp-2": "Sarah Chen", 
        "emp-3": "David Rodriguez",
        "emp-4": "Emily Watson"
    }
    employee_name = employee_mapping.get(issue.employeeId, "Unknown Employee")
    
    issue_id = f"ppe-{len(ppe_issues_db) + 1}"
    now = datetime.now().isoformat()
    
    new_issue = PPEIssue(
        id=issue_id,
        employeeName=employee_name,
        status=PPEStatus.ASSIGNED,
        lastInspection=now,
        createdAt=now,
        updatedAt=now,
        **issue.dict()
    )
    
    ppe_issues_db[issue_id] = new_issue.dict()
    
    # Update inventory
    if issue.ppeItem in ppe_inventory_db:
        ppe_inventory_db[issue.ppeItem]["assigned"] += 1
        ppe_inventory_db[issue.ppeItem]["available"] -= 1
    
    return new_issue

@router.put("/issues/{issue_id}", response_model=PPEIssue)
async def update_ppe_issue(issue_id: str, issue_update: PPEIssueUpdate):
    """Update an existing PPE issue"""
    if issue_id not in ppe_issues_db:
        raise HTTPException(status_code=404, detail="PPE issue not found")
    
    existing_issue = ppe_issues_db[issue_id]
    update_data = issue_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        existing_issue[field] = value
    
    existing_issue['updatedAt'] = datetime.now().isoformat()
    ppe_issues_db[issue_id] = existing_issue
    
    return existing_issue

@router.delete("/issues/{issue_id}")
async def delete_ppe_issue(issue_id: str):
    """Delete a PPE issue"""
    if issue_id not in ppe_issues_db:
        raise HTTPException(status_code=404, detail="PPE issue not found")
    
    # Update inventory before deleting
    issue = ppe_issues_db[issue_id]
    if issue["ppeItem"] in ppe_inventory_db and issue["status"] == "assigned":
        ppe_inventory_db[issue["ppeItem"]]["assigned"] -= 1
        ppe_inventory_db[issue["ppeItem"]]["available"] += 1
    
    del ppe_issues_db[issue_id]
    return {"message": "PPE issue deleted successfully"}

@router.post("/issues/{issue_id}/return")
async def return_ppe_issue(issue_id: str, condition: str, notes: Optional[str] = None):
    """Return a PPE item"""
    if issue_id not in ppe_issues_db:
        raise HTTPException(status_code=404, detail="PPE issue not found")
    
    issue = ppe_issues_db[issue_id]
    issue['status'] = PPEStatus.RETURNED
    issue['condition'] = condition
    issue['notes'] = notes
    issue['updatedAt'] = datetime.now().isoformat()
    
    # Update inventory
    if issue["ppeItem"] in ppe_inventory_db:
        ppe_inventory_db[issue["ppeItem"]]["assigned"] -= 1
        ppe_inventory_db[issue["ppeItem"]]["available"] += 1
    
    ppe_issues_db[issue_id] = issue
    return {"message": "PPE item returned", "issue": issue}

@router.post("/issues/{issue_id}/inspect")
async def inspect_ppe_issue(
    issue_id: str, 
    inspector: str, 
    condition: str, 
    passed: bool, 
    notes: Optional[str] = None
):
    """Record a PPE inspection"""
    if issue_id not in ppe_issues_db:
        raise HTTPException(status_code=404, detail="PPE issue not found")
    
    # Update the issue
    issue = ppe_issues_db[issue_id]
    issue['lastInspection'] = datetime.now().isoformat()
    issue['condition'] = condition
    if not passed:
        issue['status'] = PPEStatus.DAMAGED
    issue['updatedAt'] = datetime.now().isoformat()
    
    # Create inspection record
    inspection_id = f"insp-{len(ppe_inspections_db) + 1}"
    next_inspection = (datetime.now() + timedelta(days=30)).isoformat()  # Monthly inspections
    
    inspection = PPEInspection(
        id=inspection_id,
        ppeIssueId=issue_id,
        inspectionDate=datetime.now().isoformat(),
        inspector=inspector,
        condition=condition,
        passed=passed,
        notes=notes,
        nextInspection=next_inspection,
        createdAt=datetime.now().isoformat()
    )
    
    ppe_inspections_db[inspection_id] = inspection.dict()
    ppe_issues_db[issue_id] = issue
    
    return {"message": "PPE inspection recorded", "inspection": inspection}

@router.get("/inventory", response_model=List[PPEInventory])
async def get_ppe_inventory():
    """Get PPE inventory status"""
    return list(ppe_inventory_db.values())

@router.get("/inventory/{ppe_item}", response_model=PPEInventory)
async def get_ppe_item_inventory(ppe_item: str):
    """Get inventory for a specific PPE item"""
    if ppe_item not in ppe_inventory_db:
        raise HTTPException(status_code=404, detail="PPE item not found")
    return ppe_inventory_db[ppe_item]

@router.get("/inspections/{issue_id}", response_model=List[PPEInspection])
async def get_ppe_inspections(issue_id: str):
    """Get inspection history for a PPE issue"""
    inspections = [
        inspection for inspection in ppe_inspections_db.values()
        if inspection["ppeIssueId"] == issue_id
    ]
    
    # Sort by inspection date descending
    inspections.sort(key=lambda x: x["inspectionDate"], reverse=True)
    
    return inspections

@router.get("/stats")
async def get_ppe_stats():
    """Get PPE statistics for dashboard"""
    issues = list(ppe_issues_db.values())
    
    total_issues = len(issues)
    assigned_issues = len([issue for issue in issues if issue['status'] == 'assigned'])
    expired_issues = len([issue for issue in issues if 
                         datetime.fromisoformat(issue['expiryDate'].replace('Z', '+00:00')) < datetime.now()])
    due_for_inspection = len([issue for issue in issues if 
                             issue['lastInspection'] and 
                             (datetime.now() - datetime.fromisoformat(issue['lastInspection'].replace('Z', '+00:00'))).days > 30])
    
    # Compliance rate (items not expired and in good condition)
    compliant_issues = len([issue for issue in issues if 
                          issue['status'] == 'assigned' and
                          datetime.fromisoformat(issue['expiryDate'].replace('Z', '+00:00')) >= datetime.now() and
                          issue['condition'] in ['excellent', 'good']])
    
    compliance_rate = (compliant_issues / assigned_issues * 100) if assigned_issues > 0 else 0
    
    # Low stock items
    low_stock_items = len([item for item in ppe_inventory_db.values() if item['lowStock']])
    
    return {
        "totalIssues": total_issues,
        "assignedItems": assigned_issues,
        "expiredItems": expired_issues,
        "dueForInspection": due_for_inspection,
        "complianceRate": round(compliance_rate, 1),
        "lowStockItems": low_stock_items
    }

@router.get("/expiring")
async def get_expiring_ppe(days: int = 30):
    """Get PPE items expiring within the specified days"""
    now = datetime.now()
    future_date = now + timedelta(days=days)
    
    expiring_issues = []
    
    for issue in ppe_issues_db.values():
        expiry_date = datetime.fromisoformat(issue['expiryDate'].replace('Z', '+00:00'))
        
        if now <= expiry_date <= future_date and issue['status'] == 'assigned':
            days_until_expiry = (expiry_date - now).days
            expiring_issues.append({
                **issue,
                "daysUntilExpiry": days_until_expiry
            })
    
    # Sort by expiry date
    expiring_issues.sort(key=lambda x: x['expiryDate'])
    
    return {"expiringItems": expiring_issues}

@router.get("/employees/{employee_id}/ppe")
async def get_employee_ppe(employee_id: str):
    """Get all PPE assigned to a specific employee"""
    employee_issues = [
        issue for issue in ppe_issues_db.values()
        if issue["employeeId"] == employee_id and issue["status"] == "assigned"
    ]
    
    return {"employeePPE": employee_issues}