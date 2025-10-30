# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.routers import equipment, employees

# Create app WITHOUT redirect_slashes to prevent automatic redirects
app = FastAPI(
    title="MyOffice API",
    version="1.0.0",
    description="Complete office management system with equipment and employee management"
)

# CORS Configuration - This MUST come first, before any other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers - Notice NO trailing slashes in prefix
app.include_router(
    equipment.router, 
    prefix="/api/equipment",
    tags=["Equipment"]
)

app.include_router(
    employees.router, 
    prefix="/api/employees",
    tags=["Employees"]
)

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "MyOffice API is running with Supabase!",
        "version": "1.0.0",
        "endpoints": {
            "equipment": "/api/equipment",
            "employees": "/api/employees",
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
            "employees": "operational"
        }
    }

# Add a manual OPTIONS handler for preflight requests (if needed)
@app.options("/api/employees")
@app.options("/api/employees/")
@app.options("/api/equipment")
@app.options("/api/equipment/")
async def options_handler():
    return {"status": "ok"}