# app/routers/noticeboard.py 
# (Assuming this is a router file integrated into your main application)

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any

# --- Configuration ---
router = APIRouter()
# Configure templates directory (assuming a 'templates' folder is next to main.py)
templates = Jinja2Templates(directory="templates")

# --- Noticeboard Data Model (Python List of Dictionaries) ---
# This data mirrors the structure used in the React component.
NOTICEBOARD_DATA: List[Dict[str, Any]] = [
    { 
        "id": 1, 
        "title": "Q4 Performance Review Schedule", 
        "content": "All team leads must submit final reports by November 15th. Check the HR portal for personalized slots.", 
        "date": "Nov 1, 2025", 
        "category": "HR", 
        "is_pinned": True, 
        "priority": "High" 
    },
    { 
        "id": 2, 
        "title": "Mandatory Fire Drill Tomorrow at 10 AM", 
        "content": "We will be conducting a building-wide fire drill. Please evacuate to Muster Point C immediately upon hearing the alarm.", 
        "date": "Nov 1, 2025", 
        "category": "Safety", 
        "is_pinned": True, 
        "priority": "Critical" 
    },
    { 
        "id": 3, 
        "title": "Server Maintenance Tonight (11 PM - 3 AM)", 
        "content": "The main server will undergo maintenance tonight. Please save all work and log out before 11 PM.", 
        "date": "Oct 31, 2025", 
        "category": "IT", 
        "is_pinned": False, 
        "priority": "Medium" 
    },
    { 
        "id": 4, 
        "title": "New Coffee Machine in Break Room!", 
        "content": "Enjoy the new espresso machine in the 3rd-floor break room.", 
        "date": "Oct 30, 2025", 
        "category": "General", 
        "is_pinned": False, 
        "priority": "Low" 
    },
]

# --- Helper Functions (Backend logic for organizing data) ---

def organize_notices(notices: List[Dict[str, Any]]):
    """Sorts and separates notices into pinned and general lists."""
    pinned = sorted(
        [n for n in notices if n.get("is_pinned")],
        key=lambda x: x['priority'], reverse=True # Priority sorting (Critical first)
    )
    general = sorted(
        [n for n in notices if not n.get("is_pinned")],
        key=lambda x: x['date'], reverse=True # Date sorting (Newest first)
    )
    return pinned, general

# --- FastAPI Route (The View) ---

@router.get("/noticeboard", response_class=HTMLResponse, tags=["Office Management"])
async def show_noticeboard(request: Request):
    """Renders the HTML noticeboard page with data."""
    
    pinned_notices, general_notices = organize_notices(NOTICEBOARD_DATA)

    # In a real app, you would fetch and filter data from a database here.
    
    return templates.TemplateResponse(
        name="noticeboard.html", 
        context={
            "request": request,
            "pinned_notices": pinned_notices,
            "general_notices": general_notices,
            "total_pinned": len(pinned_notices),
            "total_general": len(general_notices),
            "title": "Digital Office Noticeboard"
        }
    )

# --- API Route (For Frontend Fetching) ---
# If you decide to keep the interactive React frontend, this route
# can serve the JSON data it needs.
@router.get("/api/notices", response_model=List[Dict[str, Any]], tags=["API"])
async def get_notices_api():
    """Returns raw JSON data for a JavaScript frontend."""
    return NOTICEBOARD_DATA