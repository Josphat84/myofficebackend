# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Import ALL existing and new routers ---
from app.routers import (
    equipment, employees, reports, maintenance, inventory, overtime, 
    standby, ppe, leave, 
    # NEW ROUTERS
    noticeboard, documents, training, visualization 
)

app = FastAPI(
    title="MyOffice API",
    version="1.0.0",
    description="Complete office management system with equipment and employee management",
    redirect_slashes=False
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://myoffice-black.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include ALL Routers ---
app.include_router(equipment.router, prefix="/api/equipment", tags=["Equipment"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(maintenance.router, prefix="/api/maintenance", tags=["Maintenance"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(overtime.router, prefix="/api/overtime", tags=["Overtime"])
app.include_router(standby.router, prefix="/api/standby", tags=["Standby"])
app.include_router(ppe.router, prefix="/api/ppe", tags=["PPE"])
app.include_router(leave.router, prefix="/api/leave", tags=["Leave"])

# --- Include the new routers with their prefixes ---
app.include_router(noticeboard.router, tags=["Noticeboard"]) 
app.include_router(documents.router, tags=["Document Control System"]) 
# These routers use internal prefixes defined in their files (/api/training and /api/viz)
app.include_router(training.router, tags=["Training & Certification"])
app.include_router(visualization.router, tags=["Operational Visualization"])

@app.get("/", tags=["Root"])
async def root():
    # Updated the dictionary to include all new endpoints
    return {
        "message": "MyOffice API is running with Supabase!",
        "version": "1.0.0",
        "endpoints": {
            "equipment": "/api/equipment",
            "employees": "/api/employees",
            "reports": "/api/reports",
            "maintenance": "/api/maintenance",
            "inventory": "/api/inventory",
            "overtime": "/api/overtime",
            "standby": "/api/standby",
            "ppe": "/api/ppe",
            "leave": "/api/leave",
            
            # --- NEW ENDPOINTS ---
            "documents": "/api/documents", 
            "noticeboard": "/api/notices", # Assuming the router uses this prefix
            "training": "/api/training",
            "visualization": "/api/viz",
            
            "health": "/api/health",
            "docs": "/docs"
        }
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    # Updated the dictionary to include all new services
    return {
        "status": "healthy",
        "message": "API is working with Supabase",
        "services": {
            "equipment": "operational",
            "employees": "operational",
            "reports": "operational",
            "maintenance": "operational",
            "inventory": "operational",
            "overtime": "operational",
            "standby": "operational",
            "ppe": "operational",
            "leave": "operational",
            
            # --- NEW SERVICES ---
            "documents": "operational", 
            "noticeboard": "operational", 
            "training_certification": "operational",
            "operational_viz": "operational"
        }
    }

# Vercel handler
from mangum import Mangum
handler = Mangum(app)