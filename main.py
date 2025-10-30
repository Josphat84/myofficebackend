# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import equipment, employees

app = FastAPI(
    title="MyOffice API",
    version="1.0.0",
    description="Complete office management system with equipment and employee management",
    # This prevents automatic redirect for trailing slashes
    redirect_slashes=False
)

# CORS middleware - MUST be added BEFORE routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Add your production domain here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(equipment.router, prefix="/api/equipment", tags=["Equipment"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])

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

# Vercel handler
from mangum import Mangum
handler = Mangum(app)
