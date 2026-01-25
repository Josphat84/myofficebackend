# main.py - COMPLETE UPDATED VERSION
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import logging
import traceback
import os
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== STANDBY MODELS AND STORAGE =====
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

# In-memory storage for standby
standby_db = []
next_schedule_id = 1

# ===== LIFESPAN CONTEXT MANAGER =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting MyOffice API...")
    yield
    # Shutdown
    logger.info("🛑 Shutting down MyOffice API...")

app = FastAPI(
    title="MyOffice API",
    version="1.0.0",
    description="Complete office management system with equipment, employees, and spares inventory",
    redirect_slashes=False,
    lifespan=lifespan
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

# ===== BASIC ENDPOINTS THAT SHOULD ALWAYS WORK =====
@app.get("/")
async def root():
    return {
        "message": "MyOffice API is running!",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "docs": "/docs",
            "daily_reports": "/api/daily-reports",
            "breakdowns": "/api/breakdowns",
            "standby": "/api/standby",
            "employees": "/api/employees",
            "equipment": "/api/equipment",
            "maintenance": "/api/maintenance",
            "spares": "/api/spares",
            "notices": "/api/notices"
        }
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "API is running",
        "timestamp": datetime.utcnow().isoformat(),
        "standby_schedules": len(standby_db)
    }

@app.get("/api/debug-test")
async def debug_test():
    return {"message": "Debug test - working", "status": "success"}

# ===== DIRECT STANDBY ENDPOINTS (ALWAYS WORK) =====
@app.get("/api/standby")
async def get_all_standby_schedules():
    """Get all standby schedules"""
    return standby_db

@app.post("/api/standby")
async def create_new_standby_schedule(schedule: StandbyCreate):
    """Create a new standby schedule"""
    global next_schedule_id
    
    # Calculate duration
    duration_days = (schedule.end_date - schedule.start_date).days + 1
    
    new_schedule = Standby(
        id=next_schedule_id,
        duration_days=duration_days,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        **schedule.dict()
    )
    
    standby_db.append(new_schedule)
    next_schedule_id += 1
    
    return new_schedule

@app.post("/api/standby/create")
async def create_standby_schedule_alt(schedule: StandbyCreate):
    """Alternative endpoint for creating standby schedules"""
    return await create_new_standby_schedule(schedule)

@app.get("/api/standby/{schedule_id}")
async def get_standby_schedule_by_id(schedule_id: int):
    """Get a specific standby schedule by ID"""
    for schedule in standby_db:
        if schedule.id == schedule_id:
            return schedule
    raise HTTPException(status_code=404, detail="Schedule not found")

@app.put("/api/standby/{schedule_id}")
async def update_standby_schedule(schedule_id: int, schedule_update: StandbyCreate):
    """Update a standby schedule"""
    for i, schedule in enumerate(standby_db):
        if schedule.id == schedule_id:
            # Calculate duration
            duration_days = (schedule_update.end_date - schedule_update.start_date).days + 1
            
            updated_schedule = Standby(
                id=schedule_id,
                duration_days=duration_days,
                created_at=schedule.created_at,
                updated_at=datetime.utcnow().isoformat(),
                **schedule_update.dict()
            )
            
            standby_db[i] = updated_schedule
            return updated_schedule
    
    raise HTTPException(status_code=404, detail="Schedule not found")

@app.delete("/api/standby/{schedule_id}")
async def delete_standby_schedule(schedule_id: int):
    """Delete a standby schedule"""
    for i, schedule in enumerate(standby_db):
        if schedule.id == schedule_id:
            standby_db.pop(i)
            return {"message": "Schedule deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Schedule not found")

@app.get("/api/standby/health/check")
async def standby_health_check():
    """Health check for standby system"""
    return {
        "status": "healthy",
        "service": "standby",
        "schedules_count": len(standby_db),
        "timestamp": datetime.utcnow().isoformat()
    }

# ===== INITIALIZE LOADED ROUTERS DICTIONARY =====
loaded_routers = {}

# ===== CRITICAL: SPARES ROUTER - MUST WORK FOR INVENTORY =====
logger.info("🔄 CRITICAL: Loading spares router...")

try:
    from app.routers.spares import router as spares_router
    app.include_router(spares_router, prefix="/api/spares", tags=["Spares"])
    loaded_routers["spares"] = spares_router
    logger.info("✅ SPARES ROUTER SUCCESSFULLY LOADED at /api/spares")
    
    # Log all spares routes
    logger.info("📋 Spares routes registered:")
    for route in spares_router.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            path = route.path if route.path else "/"
            logger.info(f"   {methods} /api/spares{path}")
            
except ImportError as e:
    logger.error(f"❌ CRITICAL ERROR: Failed to import spares router: {e}")
    logger.error(traceback.format_exc())
    loaded_routers["spares"] = None
except Exception as e:
    logger.error(f"❌ CRITICAL ERROR: Error including spares router: {e}")
    logger.error(traceback.format_exc())
    loaded_routers["spares"] = None

# ===== CRITICAL: DAILY REPORTS ROUTER =====
logger.info("🔄 CRITICAL: Loading daily_reports router...")

try:
    from app.routers.daily_reports import router as daily_report_router
    app.include_router(daily_report_router, prefix="/api/daily-reports", tags=["Daily Reports"])
    loaded_routers["daily_reports"] = daily_report_router
    logger.info("✅ DAILY REPORTS ROUTER SUCCESSFULLY LOADED at /api/daily-reports")
except ImportError as e:
    logger.error(f"❌ Failed to import daily_reports router: {e}")
    loaded_routers["daily_reports"] = None

# ===== BREAKDOWNS ROUTER =====
logger.info("🔄 Loading breakdowns router...")

try:
    from app.routers.breakdowns import router as breakdowns_router
    app.include_router(breakdowns_router)
    loaded_routers["breakdowns"] = breakdowns_router
    logger.info("✅ BREAKDOWNS ROUTER SUCCESSFULLY LOADED at /api/breakdowns")
except ImportError as e:
    logger.error(f"❌ Failed to import breakdowns router: {e}")
    loaded_routers["breakdowns"] = None

# ===== CRITICAL: STANDBY ROUTER - MUST WORK =====
logger.info("🔄 CRITICAL: Loading standby router...")

try:
    from app.routers.standby import router as standby_router
    app.include_router(standby_router)
    loaded_routers["standby"] = standby_router
    logger.info("✅ STANDBY ROUTER SUCCESSFULLY LOADED at /api/standby")
    
    # Log all standby routes
    logger.info("📋 Standby routes registered:")
    for route in standby_router.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            path = route.path if route.path else "/"
            logger.info(f"   {methods} {path}")
            
except ImportError as e:
    logger.error(f"❌ CRITICAL ERROR: Failed to import standby router: {e}")
    logger.error(traceback.format_exc())
    loaded_routers["standby"] = None
except Exception as e:
    logger.error(f"❌ CRITICAL ERROR: Error including standby router: {e}")
    logger.error(traceback.format_exc())
    loaded_routers["standby"] = None

# ===== NOTICEBOARD ROUTER (CRITICAL - NEW) - FIXED IMPORT PATH =====
logger.info("🔄 CRITICAL: Loading noticeboard router...")

try:
    # FIXED: Changed from 'backend.app.routers.notices' to 'app.routers.notices'
    from app.routers.notices import router as noticeboard_router
    app.include_router(noticeboard_router, prefix="/api/notices", tags=["Notices"])
    loaded_routers["noticeboard"] = noticeboard_router
    logger.info("✅ NOTICEBOARD ROUTER SUCCESSFULLY LOADED at /api/notices")
    
    # Log all noticeboard routes
    logger.info("📋 Noticeboard routes registered:")
    for route in noticeboard_router.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            path = route.path if route.path else "/"
            logger.info(f"   {methods} /api/notices{path}")
            
except ImportError as e:
    logger.error(f"❌ CRITICAL ERROR: Failed to import noticeboard router: {e}")
    logger.error(traceback.format_exc())
    loaded_routers["noticeboard"] = None
    # Add temporary direct endpoints as fallback
    logger.info("⚠️  Adding temporary notice endpoints as fallback...")
    
    # Add temporary notice models
    from pydantic import Field
    from typing import Optional as Opt
    from datetime import date as dt_date
    
    class TempNoticeCreate(BaseModel):
        title: str = Field(..., min_length=1)
        content: str = Field(..., min_length=1)
        date: dt_date
        category: str = Field(..., min_length=1)
        priority: str = Field(default="Medium")
        status: str = Field(default="Draft")
        is_pinned: bool = Field(default=False)
        author: Opt[str] = None
        department: Opt[str] = None
    
    # Add temporary endpoints
    @app.get("/api/notices")
    async def temp_get_notices():
        return {"message": "Temporary notices endpoint - router not loaded", "notices": []}
    
    @app.post("/api/notices")
    async def temp_create_notice(notice: TempNoticeCreate):
        return {
            "message": "Temporary notice created",
            "data": notice.dict(),
            "id": "temp-123",
            "created_at": datetime.utcnow().isoformat()
        }
        
except Exception as e:
    logger.error(f"❌ CRITICAL ERROR: Error including noticeboard router: {e}")
    logger.error(traceback.format_exc())
    loaded_routers["noticeboard"] = None

# ===== EMPLOYEES ROUTER (CRITICAL FOR STANDBY) =====
logger.info("🔄 Loading employees router...")

try:
    from app.routers.employees import router as employees_router
    app.include_router(employees_router, prefix="/api/employees", tags=["Employees"])
    loaded_routers["employees"] = employees_router
    logger.info("✅ EMPLOYEES ROUTER SUCCESSFULLY LOADED at /api/employees")
except ImportError as e:
    logger.error(f"❌ Failed to import employees router: {e}")
    loaded_routers["employees"] = None

# ===== EQUIPMENT ROUTER =====
logger.info("🔄 Loading equipment router...")

try:
    from app.routers.equipment import router as equipment_router
    app.include_router(equipment_router, prefix="/api/equipment", tags=["Equipment"])
    loaded_routers["equipment"] = equipment_router
    logger.info("✅ EQUIPMENT ROUTER SUCCESSFULLY LOADED at /api/equipment")
except ImportError as e:
    logger.error(f"❌ Failed to import equipment router: {e}")
    loaded_routers["equipment"] = None

# ===== MAINTENANCE ROUTER =====
logger.info("🔄 Loading maintenance router...")

try:
    from app.routers.maintenance import router as maintenance_router
    app.include_router(maintenance_router, prefix="/api/maintenance", tags=["Maintenance"])
    loaded_routers["maintenance"] = maintenance_router
    logger.info("✅ MAINTENANCE ROUTER SUCCESSFULLY LOADED at /api/maintenance")
except ImportError as e:
    logger.error(f"❌ Failed to import maintenance router: {e}")
    loaded_routers["maintenance"] = None

# ===== OTHER ROUTERS =====
logger.info("🔄 Loading other routers...")

routers_to_import = [
    "reports", "inventory", "overtime", "ppe", "documents", 
    "training", "visualization", "leaves", "sheq", "compressors"
]

for router_name in routers_to_import:
    try:
        module = __import__(f"app.routers.{router_name}", fromlist=[router_name])
        
        router_obj = None
        if hasattr(module, 'router'):
            router_obj = getattr(module, 'router')
        else:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, APIRouter):
                    router_obj = attr
                    break
        
        if router_obj is not None:
            prefix = f"/api/{router_name.replace('_', '-')}"
            app.include_router(router_obj, prefix=prefix, tags=[router_name.title().replace('_', ' ')])
            loaded_routers[router_name] = router_obj
            logger.info(f"✅ {router_name.title().replace('_', ' ')} router included at {prefix}")
        else:
            logger.warning(f"⚠️ No APIRouter found in {router_name} module")
            loaded_routers[router_name] = None
            
    except Exception as e:
        logger.error(f"❌ Failed to import {router_name} router: {e}")
        loaded_routers[router_name] = None

# ===== DEBUG ENDPOINT FOR NOTICEBOARD =====
@app.get("/api/debug-notices-router")
async def debug_notices_router():
    """Debug endpoint to check noticeboard router status"""
    noticeboard_router = loaded_routers.get("noticeboard")
    
    if noticeboard_router:
        # List all routes in the noticeboard router
        routes = []
        for route in noticeboard_router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = list(route.methods) if hasattr(route, 'methods') else []
                path = route.path
                routes.append({
                    'methods': methods,
                    'path': path,
                    'name': getattr(route, 'name', 'N/A')
                })
        
        return {
            "status": "loaded",
            "router": "noticeboard",
            "total_routes": len(routes),
            "routes": routes,
            "note": "Router is successfully loaded"
        }
    else:
        return {
            "status": "not_loaded",
            "router": "noticeboard",
            "error": "Router not found in loaded_routers",
            "available_routers": list(loaded_routers.keys()),
            "fix_steps": [
                "1. Check that app/routers/notices.py exists",
                "2. Check for import errors in notices.py",
                "3. Check that notices.py exports a 'router' variable"
            ]
        }

# ===== DIRECT NOTICE ENDPOINTS AS FALLBACK (Always available) =====
logger.info("🔄 Adding direct notice endpoints as guaranteed fallback...")

# Direct notice models
from pydantic import Field
from typing import Optional as Opt
from datetime import date as dt_date
import uuid

class DirectNoticeCreate(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    date: dt_date
    category: str = Field(..., min_length=1)
    priority: str = Field(default="Medium")
    status: str = Field(default="Draft")
    is_pinned: bool = Field(default=False)
    author: Opt[str] = None
    department: Opt[str] = None
    expires_at: Opt[dt_date] = None
    target_audience: Opt[str] = None
    notification_type: Opt[str] = None
    requires_acknowledgment: bool = Field(default=False)
    attachment_name: Opt[str] = None
    attachment_url: Opt[str] = None
    attachment_size: Opt[str] = None

# In-memory storage for notices as fallback
notices_db = []

# Direct endpoints that will always work
@app.get("/api/direct-notices")
async def get_direct_notices():
    """Direct endpoint to get notices - always works"""
    return notices_db

@app.post("/api/direct-notices")
async def create_direct_notice(notice: DirectNoticeCreate):
    """Direct endpoint to create a notice - always works"""
    notice_id = str(uuid.uuid4())
    new_notice = {
        "id": notice_id,
        **notice.dict(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    notices_db.append(new_notice)
    return new_notice

@app.get("/api/direct-notices/{notice_id}")
async def get_direct_notice(notice_id: str):
    """Direct endpoint to get a specific notice"""
    for notice in notices_db:
        if notice.get("id") == notice_id:
            return notice
    raise HTTPException(status_code=404, detail="Notice not found")

# ===== FALLBACK ROUTES FOR CRITICAL ENDPOINTS =====

# Fallback for spares if router not loaded
@app.get("/api/spares")
@app.get("/api/spares/")
async def spares_fallback():
    """Fallback endpoint if spares router doesn't load"""
    if loaded_routers.get("spares"):
        return {
            "message": "Spares router is loaded",
            "use_endpoint": "/api/spares for full functionality"
        }
    else:
        return {
            "message": "Spares router not loaded",
            "status": "fallback_mode",
            "fix_steps": [
                "1. Check that app/routers/spares.py exists",
                "2. Check for syntax errors in spares.py",
                "3. Check supabase_client.py connection",
                "4. Restart the backend server"
            ]
        }

# Fallback for employees if router not loaded
@app.get("/api/employees")
@app.get("/api/employees/")
async def employees_fallback():
    """Fallback endpoint if employees router doesn't load"""
    if loaded_routers.get("employees"):
        return {
            "message": "Employees router is loaded",
            "use_endpoint": "/api/employees for full functionality"
        }
    else:
        return {
            "message": "Employees router not loaded",
            "status": "fallback_mode",
            "note": "Check app/routers/employees.py for errors"
        }

# Fallback for notices if router not loaded
@app.get("/api/notices")
@app.get("/api/notices/")
async def notices_fallback():
    """Fallback endpoint if noticeboard router doesn't load"""
    if loaded_routers.get("noticeboard"):
        return {
            "message": "Noticeboard router is loaded",
            "use_endpoint": "/api/notices for full functionality"
        }
    else:
        return {
            "message": "Noticeboard router not loaded - using fallback",
            "status": "fallback_mode",
            "direct_endpoints": [
                "GET /api/direct-notices - Get all notices (always works)",
                "POST /api/direct-notices - Create a notice (always works)",
                "GET /api/direct-notices/{id} - Get a specific notice"
            ],
            "fix_steps": [
                "1. Check that app/routers/notices.py exists",
                "2. Check for syntax errors in notices.py",
                "3. Check supabase_client.py connection",
                "4. Restart the backend server"
            ]
        }

# ===== DEBUG ENDPOINTS =====
@app.get("/api/debug-all-routes")
async def debug_all_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods),
                'name': getattr(route, 'name', 'N/A')
            })
    
    return {
        "all_routes": routes,
        "total_routes": len(routes),
        "spares_routes": [r for r in routes if 'spares' in r['path']],
        "standby_routes": [r for r in routes if 'standby' in r['path']],
        "notices_routes": [r for r in routes if 'notices' in r['path']],
        "direct_notices_routes": [r for r in routes if 'direct-notices' in r['path']],
        "employees_routes": [r for r in routes if 'employees' in r['path']],
        "equipment_routes": [r for r in routes if 'equipment' in r['path']],
        "maintenance_routes": [r for r in routes if 'maintenance' in r['path']],
        "routers_loaded": {k: v is not None for k, v in loaded_routers.items()}
    }

@app.get("/api/debug-router-status")
async def debug_router_status():
    return {
        "critical_routers": {
            "spares": loaded_routers.get("spares") is not None,
            "standby": loaded_routers.get("standby") is not None,
            "noticeboard": loaded_routers.get("noticeboard") is not None,
            "employees": loaded_routers.get("employees") is not None,
            "daily_reports": loaded_routers.get("daily_reports") is not None,
            "breakdowns": loaded_routers.get("breakdowns") is not None,
            "equipment": loaded_routers.get("equipment") is not None,
            "maintenance": loaded_routers.get("maintenance") is not None
        },
        "all_routers": {k: v is not None for k, v in loaded_routers.items()},
        "direct_endpoints_available": {
            "notices": True,  # /api/direct-notices always works
            "standby": True   # /api/standby always works
        },
        "note": "Check /api/spares/health/check for spares health"
    }

# ===== HEALTH CHECK ENDPOINTS =====
@app.get("/api/spares/health")
async def spares_health_check_fallback():
    """Health check for spares router"""
    spares_router = loaded_routers.get("spares")
    if spares_router:
        return {
            "status": "router_loaded",
            "message": "Spares router is loaded",
            "use_endpoint": "/api/spares/health/check for detailed health"
        }
    else:
        return {
            "status": "router_not_loaded",
            "message": "Spares router failed to load",
            "fix_steps": [
                "1. Check that app/routers/spares.py exists",
                "2. Check for syntax errors in spares.py",
                "3. Check supabase_client.py connection",
                "4. Restart the backend server"
            ]
        }

@app.get("/api/employees/health")
async def employees_health_check():
    """Health check for employees router"""
    employees_router = loaded_routers.get("employees")
    if employees_router:
        return {
            "status": "healthy",
            "service": "employees",
            "message": "Employees router is loaded and ready"
        }
    else:
        return {
            "status": "unhealthy",
            "service": "employees",
            "message": "Employees router not loaded"
        }

@app.get("/api/notices/health")
async def notices_health_check():
    """Health check for noticeboard router"""
    noticeboard_router = loaded_routers.get("noticeboard")
    if noticeboard_router:
        return {
            "status": "healthy",
            "service": "noticeboard",
            "message": "Noticeboard router is loaded and ready",
            "endpoints_available": [
                "GET /api/notices - Get all notices",
                "POST /api/notices - Create a notice",
                "GET /api/notices/{id} - Get a specific notice",
                "PUT /api/notices/{id} - Update a notice",
                "DELETE /api/notices/{id} - Delete a notice"
            ]
        }
    else:
        return {
            "status": "unhealthy_but_fallback_available",
            "service": "noticeboard",
            "message": "Noticeboard router not loaded, but fallback endpoints are available",
            "fallback_endpoints": [
                "GET /api/direct-notices - Get all notices",
                "POST /api/direct-notices - Create a notice",
                "GET /api/direct-notices/{id} - Get a specific notice"
            ],
            "fix_steps": [
                "1. Check that app/routers/notices.py exists",
                "2. Check supabase_client.py connection",
                "3. Check database table 'notices' exists in Supabase"
            ]
        }

# ===== TEST ENDPOINTS =====
@app.get("/api/test-spares-connection")
async def test_spares_connection():
    """Test endpoint for spares router"""
    return {
        "status": "test",
        "message": "Spares connection test",
        "spares_loaded": loaded_routers.get("spares") is not None,
        "backend": "FastAPI",
        "endpoints_available": [
            "GET /api/spares",
            "POST /api/spares",
            "GET /api/spares/{id}",
            "PUT /api/spares/{id}",
            "DELETE /api/spares/{id}",
            "GET /api/spares/stats/summary",
            "GET /api/spares/suggestions/{field}",
            "GET /api/spares/health/check"
        ] if loaded_routers.get("spares") else [],
        "note": "Spares inventory management system"
    }

@app.get("/api/test-standby-connection")
async def test_standby_connection():
    """Test endpoint for standby system"""
    return {
        "status": "test",
        "message": "Standby connection test",
        "standalone_endpoints_active": True,
        "schedules_count": len(standby_db),
        "backend": "FastAPI",
        "endpoints_available": [
            "GET /api/standby",
            "POST /api/standby",
            "POST /api/standby/create",
            "GET /api/standby/{id}",
            "PUT /api/standby/{id}",
            "DELETE /api/standby/{id}",
            "GET /api/standby/health/check"
        ],
        "note": "Standby system is working with in-memory storage"
    }

@app.get("/api/test-notices-connection")
async def test_notices_connection():
    """Test endpoint for noticeboard system"""
    noticeboard_router = loaded_routers.get("noticeboard")
    return {
        "status": "test",
        "message": "Noticeboard connection test",
        "noticeboard_loaded": noticeboard_router is not None,
        "backend": "FastAPI",
        "router_endpoints": [
            "GET /api/notices",
            "POST /api/notices",
            "GET /api/notices/{id}",
            "PUT /api/notices/{id}",
            "DELETE /api/notices/{id}"
        ] if noticeboard_router else [],
        "direct_endpoints_always_available": [
            "GET /api/direct-notices",
            "POST /api/direct-notices",
            "GET /api/direct-notices/{id}"
        ],
        "note": "Noticeboard management system with fallback support"
    }

@app.get("/api/test-all-connections")
async def test_all_connections():
    """Test all critical endpoints"""
    test_results = {}
    
    # Test basic health
    try:
        response = await health_check()
        test_results["basic_health"] = {"status": "success", "data": response}
    except Exception as e:
        test_results["basic_health"] = {"status": "error", "error": str(e)}
    
    # Test each critical router
    critical_routers = ["spares", "standby", "noticeboard", "employees", "daily_reports", "breakdowns", "equipment", "maintenance"]
    
    for router_name in critical_routers:
        router = loaded_routers.get(router_name)
        test_results[router_name] = {
            "loaded": router is not None,
            "endpoints": []
        }
        
        if router:
            try:
                # Try to get routes from router
                routes = []
                for route in router.routes:
                    if hasattr(route, 'methods') and hasattr(route, 'path'):
                        methods = list(route.methods) if hasattr(route, 'methods') else []
                        routes.append(f"{methods} {route.path}")
                
                test_results[router_name]["endpoints"] = routes[:5]  # First 5 endpoints
                test_results[router_name]["total_endpoints"] = len(routes)
            except Exception as e:
                test_results[router_name]["error"] = str(e)
    
    # Test direct notice endpoints
    test_results["direct_notices"] = {
        "available": True,
        "endpoints": [
            "GET /api/direct-notices",
            "POST /api/direct-notices",
            "GET /api/direct-notices/{id}"
        ],
        "note": "Always available as fallback"
    }
    
    return {
        "status": "test_complete",
        "timestamp": datetime.utcnow().isoformat(),
        "results": test_results
    }

# ===== STARTUP EVENT =====
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Application starting up...")
    
    # Log loaded routers
    loaded_count = sum(1 for router in loaded_routers.values() if router is not None)
    total_count = len(loaded_routers)
    logger.info(f"📈 Router loading summary: {loaded_count}/{total_count} routers loaded")
    
    # Check critical routers
    critical_routers = {
        "spares": "Spares Inventory",
        "standby": "Standby Scheduler",
        "noticeboard": "Noticeboard Management",
        "employees": "Employees",
        "daily_reports": "Daily Reports",
        "breakdowns": "Breakdowns",
        "equipment": "Equipment",
        "maintenance": "Maintenance"
    }
    
    for router_name, display_name in critical_routers.items():
        if loaded_routers.get(router_name):
            logger.info(f"✅ {display_name} router SUCCESSFULLY LOADED!")
        else:
            logger.error(f"❌ {display_name} router FAILED TO LOAD!")
    
    # Log standalone standby status
    logger.info("📊 Standalone Standby System Status:")
    logger.info(f"   ✅ Direct endpoints available at /api/standby")
    logger.info(f"   📋 Currently {len(standby_db)} schedules in memory")
    
    # Log noticeboard status
    if loaded_routers.get("noticeboard"):
        logger.info("📊 Noticeboard System Status:")
        logger.info(f"   ✅ Noticeboard endpoints available at /api/notices")
        logger.info(f"   📋 Database: Supabase table 'notices'")
    else:
        logger.warning("⚠️  Noticeboard router failed to load! Using fallback endpoints")
        logger.info("   ✅ Fallback endpoints available at /api/direct-notices")
    
    # Log direct notice fallback
    logger.info("📊 Direct Notice Fallback System:")
    logger.info(f"   ✅ Always available at /api/direct-notices")
    logger.info(f"   📋 Currently {len(notices_db)} notices in memory fallback")
    
    # Log all routes for debugging
    logger.info("📋 All registered routes by category:")
    
    route_categories = {
        "spares": [],
        "standby": [],
        "notices": [],
        "direct_notices": [],
        "employees": [],
        "equipment": [],
        "maintenance": [],
        "daily_reports": [],
        "breakdowns": [],
        "other": []
    }
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            path_info = f"{methods} {route.path}"
            
            categorized = False
            for category in route_categories.keys():
                if f'/api/{category.replace("_", "-")}' in str(route.path):
                    route_categories[category].append(path_info)
                    categorized = True
                    break
            
            if not categorized and '/api/' in str(route.path):
                route_categories["other"].append(path_info)
    
    for category, routes in route_categories.items():
        if routes:
            logger.info(f"📝 {category.replace('_', ' ').title()} routes ({len(routes)}):")
            for route in routes[:3]:  # Show first 3 routes
                logger.info(f"   {route}")
            if len(routes) > 3:
                logger.info(f"   ... and {len(routes) - 3} more")
    
    # Log total endpoints
    total_endpoints = sum(len(routes) for routes in route_categories.values())
    logger.info(f"📊 Total endpoints registered: {total_endpoints}")
    
    # Special notice for noticeboard routes
    if route_categories["notices"]:
        logger.info("📢 Noticeboard System is ready at:")
        for route in route_categories["notices"][:5]:  # Show first 5 notice routes
            logger.info(f"   {route}")
    
    # Special notice for direct notice routes
    if route_categories["direct_notices"]:
        logger.info("📢 Direct Notice Fallback System is ready at:")
        for route in route_categories["direct_notices"]:
            logger.info(f"   {route}")

# ===== SHUTDOWN EVENT =====
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Application shutting down...")

# ===== VERCELL HANDLER =====
from mangum import Mangum
handler = Mangum(app)

logger.info("🏁 Main.py setup completed - All routers initialized including Spares, Standby, and Noticeboard")
logger.info("🏁 Direct fallback endpoints available at /api/direct-notices")