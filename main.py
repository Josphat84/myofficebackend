# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import equipment, employees, reports, maintenance, inventory, overtime, standby

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

# Include routers
app.include_router(equipment.router, prefix="/api/equipment", tags=["Equipment"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(maintenance.router, prefix="/api/maintenance", tags=["Maintenance"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(overtime.router, prefix="/api/overtime", tags=["Overtime"])
app.include_router(standby.router, prefix="/api/standby", tags=["Standby"])

@app.get("/", tags=["Root"])
async def root():
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
            "health": "/api/health",
            "docs": "/docs"
        }
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
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
            "standby": "operational"
        }
    }

# Vercel handler
from mangum import Mangum
handler = Mangum(app)