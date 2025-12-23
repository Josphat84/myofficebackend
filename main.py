# backend/main.py
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import logging
import traceback
import os
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Lifespan context manager
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
    description="Complete office management system with equipment and employee management",
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
            "daily_reports": "/api/daily-reports"
        }
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "API is running",
        "timestamp": "2024-01-15T10:00:00Z"
    }

@app.get("/api/debug-test")
async def debug_test():
    return {"message": "Debug test - working", "status": "success"}

# ===== CRITICAL FIX: DAILY REPORTS ROUTER - NO FALLBACK, MUST WORK =====
logger.info("🔄 CRITICAL: Loading daily_reports router from app.routers...")

# Remove all fallback logic - we need REAL database connection
try:
    # CORRECT: Import from app.routers.daily_reports (not backend.app.routers)
    from app.routers.daily_reports import router as daily_report_router
    
    # Include the router with the correct prefix
    app.include_router(daily_report_router, prefix="/api/daily-reports", tags=["Daily Reports"])
    logger.info("✅ DAILY REPORTS ROUTER SUCCESSFULLY LOADED at /api/daily-reports")
    daily_reports_loaded = True
    
    # Log the routes
    logger.info("📋 Daily Reports routes found:")
    for route in daily_report_router.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            logger.info(f"   {methods} /api/daily-reports{route.path}")
            
except ImportError as e:
    logger.error(f"❌ CRITICAL ERROR: Failed to import daily_reports router: {e}")
    logger.error(traceback.format_exc())
    daily_reports_loaded = False
    # NO FALLBACK - We need the real router
    raise ImportError(f"CRITICAL: Cannot load daily_reports router: {e}. Check that app/routers/daily_reports.py exists and contains 'router = APIRouter()'")
except Exception as e:
    logger.error(f"❌ CRITICAL ERROR: Error including daily_reports router: {e}")
    logger.error(traceback.format_exc())
    daily_reports_loaded = False
    raise

# ===== ROUTER IMPORTS AND INCLUSION FOR OTHER ROUTERS =====
logger.info("🔄 Starting other router imports...")

# Updated routers list - EXCLUDING daily_reports since we already loaded it
routers_to_import = [
    "equipment", "employees", "reports", "inventory", 
    "overtime", "standby", "ppe", "noticeboard", "documents", 
    "training", "visualization", "leaves", "sheq",
    "breakdowns", "compressors"
]

loaded_routers = {}
loaded_routers["daily_reports"] = daily_report_router if daily_reports_loaded else None

for router_name in routers_to_import:
    try:
        logger.info(f"🔄 Loading {router_name} router...")
        
        # Normal import for other routers
        module = __import__(f"app.routers.{router_name}", fromlist=[router_name])
        
        # Try to get the router object
        router_obj = None
        
        # Look for 'router' attribute
        if hasattr(module, 'router'):
            router_obj = getattr(module, 'router')
        else:
            # Try to find any APIRouter in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, APIRouter):
                    router_obj = attr
                    break
        
        if router_obj is None:
            logger.warning(f"⚠️ No APIRouter found in {router_name} module")
            continue
        
        loaded_routers[router_name] = router_obj
        
        # Include router with proper prefix
        prefix = f"/api/{router_name.replace('_', '-')}"
        app.include_router(router_obj, prefix=prefix, tags=[router_name.title().replace('_', ' ')])
        logger.info(f"✅ {router_name.title().replace('_', ' ')} router included at {prefix}")
        
    except Exception as e:
        logger.error(f"❌ Failed to import {router_name} router: {e}")
        logger.error(traceback.format_exc())
        loaded_routers[router_name] = None

# ===== MANUALLY INCLUDE THE SELF-CONTAINED MAINTENANCE ROUTER =====
try:
    logger.info("🔄 Loading self-contained maintenance router...")
    from app.routers.maintenance import router as maintenance_router
    app.include_router(maintenance_router, prefix="/api/maintenance", tags=["Maintenance"])
    loaded_routers["maintenance"] = maintenance_router
    logger.info("✅ Self-contained Maintenance router included at /api/maintenance")
except Exception as e:
    logger.error(f"❌ Failed to import self-contained maintenance router: {e}")
    logger.error(traceback.format_exc())

# ===== SUCCESS: DAILY REPORTS IS WORKING CHECK =====
@app.get("/api/daily-reports-success-check")
async def daily_reports_success_check():
    """Check if daily_reports is actually working"""
    if daily_reports_loaded:
        return {
            "status": "SUCCESS",
            "message": "Daily Reports router is properly loaded and working!",
            "endpoints_available": [
                "POST /api/daily-reports - Create/update report",
                "GET /api/daily-reports - Get all reports",
                "GET /api/daily-reports/health/check - Health check",
                "GET /api/daily-reports/stats/summary - Get statistics"
            ],
            "database_connection": "Will be tested on first request",
            "note": "If you see this, the router is loaded correctly!"
        }
    else:
        return {
            "status": "FAILED",
            "message": "Daily Reports router failed to load",
            "fix_steps": [
                "1. Check that app/routers/daily_reports.py exists",
                "2. Check that daily_reports.py has 'router = APIRouter()'",
                "3. Check for import errors in daily_reports.py",
                "4. Check supabase_client.py connection"
            ]
        }

# ===== TEMPORARY BREAKDOWNS FALLBACK ENDPOINTS =====
if "breakdowns" not in loaded_routers or loaded_routers["breakdowns"] is None:
    logger.warning("⚠️ Breakdowns router not loaded, creating temporary fallback endpoints")
    
    @app.get("/api/breakdowns")
    async def temp_breakdowns_endpoint():
        """Temporary fallback endpoint for breakdowns"""
        return {
            "status": "fallback",
            "message": "Breakdowns router is not properly loaded. This is a temporary endpoint.",
            "test_data": [
                {
                    "id": "test-001",
                    "artisan_name": "Test Artisan",
                    "date": "2024-01-15",
                    "machine_id": "LOCO-5L-001",
                    "machine_description": "Test Machine - 5 Level 2.5 Ton SHEPCO Locomotive",
                    "location": "5 Level",
                    "breakdown_type": "Mechanical failure",
                    "status": "logged",
                    "breakdown_duration": 120,
                    "response_time": 30,
                    "created_at": "2024-01-15T10:00:00Z"
                }
            ]
        }
    
    @app.get("/api/breakdowns/health")
    async def temp_breakdowns_health():
        """Temporary health check for breakdowns"""
        return {
            "status": "unhealthy",
            "service": "breakdowns",
            "message": "Breakdowns router not loaded. Using temporary endpoints.",
            "instructions": "Check that breakdowns.py exists in app/routers/ and contains an APIRouter named 'router'"
        }

# ===== TEMPORARY COMPRESSORS FALLBACK ENDPOINTS =====
if "compressors" not in loaded_routers or loaded_routers["compressors"] is None:
    logger.warning("⚠️ Compressors router not loaded, creating temporary fallback endpoints")
    
    @app.get("/api/compressors")
    async def temp_compressors_endpoint():
        """Temporary fallback endpoint for compressors"""
        return {
            "status": "fallback",
            "message": "Compressors router is not properly loaded. This is a temporary endpoint.",
            "test_data": [
                {
                    "id": "test-001",
                    "name": "Compressor #1",
                    "model": "Atlas Copco GA37",
                    "capacity": "37 kW",
                    "status": "running",
                    "location": "Main Plant",
                    "color": "bg-blue-500",
                    "total_running_hours": 1250.5,
                    "total_loaded_hours": 950.3,
                    "manufacturer": "Atlas Copco",
                    "created_at": "2024-01-15T10:00:00Z"
                },
                {
                    "id": "test-002",
                    "name": "Compressor #2",
                    "model": "Ingersoll Rand SSR",
                    "capacity": "30 kW",
                    "status": "standby",
                    "location": "Production",
                    "color": "bg-green-500",
                    "total_running_hours": 850.2,
                    "total_loaded_hours": 620.7,
                    "manufacturer": "Ingersoll Rand",
                    "created_at": "2024-01-15T10:00:00Z"
                }
            ]
        }
    
    @app.get("/api/compressors/stats")
    async def temp_compressors_stats():
        """Temporary stats endpoint for compressors"""
        return {
            "total_compressors": 2,
            "total_running_hours": 2100.7,
            "total_loaded_hours": 1571.0,
            "avg_efficiency": 74.8,
            "active_compressors": 2,
            "upcoming_services": 1,
            "urgent_alerts": 0
        }

# ===== DEBUG ENDPOINTS (DEFINED AFTER ROUTERS) =====
@app.get("/api/debug-daily-reports-status")
async def debug_daily_reports_status():
    """Check if daily_reports router is loaded"""
    try:
        daily_reports_router = loaded_routers.get("daily_reports")
        
        if not daily_reports_router:
            return {
                "status": "missing",
                "message": "Daily_reports router not loaded",
                "loaded_routers": list(loaded_routers.keys()),
                "note": "Check that daily_reports.py exists in app/routers/ and contains an APIRouter named 'router'",
                "fix": "The router must be imported DIRECTLY, not dynamically"
            }
        
        # Check routes in the router
        routes = []
        for route in daily_reports_router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                routes.append({
                    'methods': list(route.methods),
                    'path': route.path,
                    'name': getattr(route, 'name', 'N/A')
                })
        
        # Check if it has the critical POST endpoint
        has_post = any('POST' in route['methods'] for route in routes)
        has_get = any('GET' in route['methods'] for route in routes)
        has_health = any('/health/check' in route['path'] for route in routes)
        
        return {
            "status": "loaded",
            "router_routes": routes,
            "total_routes": len(routes),
            "has_post_endpoint": has_post,
            "has_get_endpoint": has_get,
            "has_health_endpoint": has_health,
            "critical_endpoints_present": has_post and has_get and has_health,
            "message": "✅ Daily Reports router is properly loaded!" if has_post and has_get and has_health else "⚠️ Some endpoints may be missing"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/api/debug-compressors-status")
async def debug_compressors_status():
    """Check if compressors router is loaded"""
    try:
        compressors_router = loaded_routers.get("compressors")
        
        if not compressors_router:
            return {
                "status": "missing",
                "message": "Compressors router not loaded",
                "loaded_routers": list(loaded_routers.keys()),
                "temporary_endpoints_available": [
                    "GET /api/compressors",
                    "GET /api/compressors/stats"
                ]
            }
        
        # Check routes in the router
        routes = []
        for route in compressors_router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                routes.append({
                    'methods': list(route.methods),
                    'path': route.path
                })
        
        return {
            "status": "loaded",
            "router_routes": routes,
            "total_routes": len(routes),
            "full_endpoints": [f"GET /api/compressors{route['path']}" for route in routes],
            "expected_endpoints": [
                "GET /api/compressors/compressors - Get all compressors",
                "POST /api/compressors/compressors - Create compressor",
                "GET /api/compressors/stats - Get compressor statistics",
                "GET /api/compressors/service-due - Get upcoming services",
                "POST /api/compressors/daily-entries/cumulative - Create daily entry",
                "GET /api/compressors/analytics/performance-metrics - Get performance metrics",
                "GET /api/compressors/analytics/trends - Get trend analysis",
                "GET /api/compressors/analytics/comparison - Get comparison analytics",
                "GET /api/compressors/management/summary - Get management summary",
                "POST /api/compressors/export - Export data",
                "POST /api/compressors/import - Import data",
                "POST /api/compressors/service-records - Create service record"
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/debug-all-routes")
async def debug_all_routes():
    """List all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods),
                'name': getattr(route, 'name', 'N/A')
            })
    
    # Categorize routes
    route_categories = {
        "daily_reports_routes": [r for r in routes if 'daily-reports' in r['path']],
        "work_order_routes": [r for r in routes if 'work-orders' in r['path']],
        "maintenance_routes": [r for r in routes if 'maintenance' in r['path'] and 'work-orders' not in r['path']],
        "leaves_routes": [r for r in routes if 'leaves' in r['path']],
        "overtime_routes": [r for r in routes if 'overtime' in r['path']],
        "sheq_routes": [r for r in routes if 'sheq' in r['path']],
        "breakdowns_routes": [r for r in routes if 'breakdowns' in r['path']],
        "compressors_routes": [r for r in routes if 'compressors' in r['path']]
    }
    
    result = {
        "all_routes": routes,
        **route_categories,
        "total_routes": len(routes)
    }
    
    # Add counts for each category
    for category_name, category_routes in route_categories.items():
        result[f"total_{category_name}"] = len(category_routes)
    
    return result

@app.get("/api/debug-router-imports")
async def debug_router_imports():
    """Show which routers imported successfully"""
    all_routers = ["daily_reports"] + routers_to_import + ["maintenance"]
    loaded = [r for r in all_routers if r in loaded_routers and loaded_routers[r] is not None]
    missing = [r for r in all_routers if r not in loaded_routers or loaded_routers[r] is None]
    
    return {
        "routers_to_import": all_routers,
        "loaded_routers": loaded,
        "missing_routers": missing,
        "daily_reports_status": "✅ LOADED" if daily_reports_loaded else "❌ MISSING",
        "note": "work_orders and job_cards are now part of the self-contained maintenance router at /api/maintenance"
    }

@app.get("/api/debug-supabase-connection")
async def debug_supabase_connection():
    """Debug Supabase connection for daily reports"""
    try:
        # Since daily_reports.py has its own supabase client, we need to import it
        if daily_reports_loaded:
            # CORRECT: Import from app.routers.daily_reports (not backend.app.routers)
            from app.routers.daily_reports import supabase
            
            if supabase is None:
                return {
                    "status": "error",
                    "message": "Supabase client is None in daily_reports.py - check .env file",
                    "supabase_url_set": bool(os.getenv("SUPABASE_URL")),
                    "supabase_key_set": bool(os.getenv("SUPABASE_KEY")),
                    "env_file_exists": os.path.exists(".env"),
                    "daily_reports_loaded": daily_reports_loaded
                }
            
            # Try to query the daily_reports table
            try:
                result = supabase.table("daily_reports").select("*", count="exact").limit(1).execute()
                
                return {
                    "status": "success",
                    "message": "Supabase connection successful via daily_reports.py",
                    "table_exists": True,
                    "row_count": len(result.data) if result.data else 0,
                    "daily_reports_loaded": daily_reports_loaded,
                    "can_save_data": True
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Supabase query failed: {str(e)}",
                    "error_details": "Check if daily_reports table exists in Supabase",
                    "daily_reports_loaded": daily_reports_loaded
                }
        else:
            return {
                "status": "error",
                "message": "Daily Reports app not loaded, cannot check Supabase",
                "daily_reports_loaded": daily_reports_loaded
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Debug error: {str(e)}",
            "traceback": traceback.format_exc()
        }

# ===== HEALTH CHECK ENDPOINTS =====
@app.get("/api/daily-reports/health")
async def daily_reports_health_check():
    """Quick health check for daily_reports service"""
    try:
        if daily_reports_loaded:
            # This endpoint will be overridden by the actual router
            return {
                "status": "checking",
                "service": "daily_reports",
                "message": "Router is loaded, checking actual endpoint...",
                "note": "Use /api/daily-reports/health/check for the real health check"
            }
        else:
            return {
                "status": "unhealthy", 
                "service": "daily_reports",
                "message": "Daily_reports router not loaded in main.py",
                "note": "Check that daily_reports.py exists in app/routers/",
                "fix": "Make sure daily_reports.py has 'router = APIRouter()' and proper imports"
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "daily_reports",
            "error": str(e)
        }

@app.get("/api/compressors/health")
async def compressors_health_check():
    """Quick health check for compressors service"""
    try:
        compressors_router = loaded_routers.get("compressors")
        if compressors_router:
            return {
                "status": "healthy",
                "service": "compressors",
                "message": "Compressors router is loaded and ready",
                "endpoints_available": [
                    "/api/compressors/compressors",
                    "/api/compressors/stats",
                    "/api/compressors/service-due",
                    "/api/compressors/analytics/comparison",
                    "/api/compressors/analytics/trends"
                ]
            }
        else:
            return {
                "status": "unhealthy", 
                "service": "compressors",
                "message": "Compressors router not found",
                "temporary_endpoints": [
                    "/api/compressors",
                    "/api/compressors/stats"
                ]
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "compressors",
            "error": str(e)
        }

# ===== TEST ENDPOINTS FOR QUICK VERIFICATION =====
@app.get("/api/test-daily-reports-connection")
async def test_daily_reports_connection():
    """Test endpoint to verify daily reports is working"""
    return {
        "status": "test",
        "message": "Daily Reports connection test",
        "backend": "FastAPI",
        "daily_reports_loaded": daily_reports_loaded,
        "real_database": "YES - Will save to Supabase",
        "test_data": {
            "date": "2024-01-15",
            "plant_availability_percent": 95.5,
            "dam_level": 7.2,
            "power_availability": "normal"
        },
        "next_steps": [
            "1. Go to /api/daily-reports-success-check to verify",
            "2. Go to /api/debug-daily-reports-status to see endpoints",
            "3. Go to /api/debug-supabase-connection to check database",
            "4. Use POST /api/daily-reports to save real data"
        ]
    }

# ===== STARTUP EVENT =====
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Application starting up...")
    
    # Log all routes
    logger.info("📋 Registered routes:")
    
    # Categorize and log routes
    route_categories = {
        "daily_reports": [],
        "work_orders": [],
        "maintenance": [],
        "leaves": [],
        "overtime": [],
        "sheq": [],
        "breakdowns": [],
        "compressors": []
    }
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            path_info = f"   {methods} {route.path}"
            
            if '/api/daily-reports' in str(route.path):
                route_categories["daily_reports"].append(path_info)
            elif '/api/maintenance/work-orders' in str(route.path):
                route_categories["work_orders"].append(path_info)
            elif '/api/maintenance' in str(route.path) and '/api/maintenance/work-orders' not in str(route.path):
                route_categories["maintenance"].append(path_info)
            elif '/api/leaves' in str(route.path):
                route_categories["leaves"].append(path_info)
            elif '/api/overtime' in str(route.path):
                route_categories["overtime"].append(path_info)
            elif '/api/sheq' in str(route.path):
                route_categories["sheq"].append(path_info)
            elif '/api/breakdowns' in str(route.path):
                route_categories["breakdowns"].append(path_info)
            elif '/api/compressors' in str(route.path):
                route_categories["compressors"].append(path_info)
    
    # Log each category
    for category, routes in route_categories.items():
        if routes:
            logger.info(f"📝 {category.title()} routes found ({len(routes)}):")
            for route in routes[:5]:  # Show first 5 routes
                logger.info(route)
            if len(routes) > 5:
                logger.info(f"   ... and {len(routes) - 5} more")
        else:
            logger.warning(f"⚠️ No {category} routes found!")
    
    # Log daily reports status - CRITICAL INFORMATION
    if daily_reports_loaded:
        logger.info("🎉 DAILY REPORTS ROUTER SUCCESSFULLY LOADED!")
        logger.info("✅ Real database operations will work")
        logger.info("✅ POST /api/daily-reports will save to Supabase")
        logger.info("✅ GET /api/daily-reports will fetch from Supabase")
    else:
        logger.error("❌❌❌ DAILY REPORTS ROUTER FAILED TO LOAD! ❌❌❌")
        logger.error("❌ Data will NOT be saved to database")
        logger.error("❌ Check app/routers/daily_reports.py exists")
        logger.error("❌ Check for import errors in daily_reports.py")
    
    # Log a summary
    loaded_count = sum(1 for router in loaded_routers.values() if router is not None)
    total_count = len(loaded_routers)
    logger.info(f"📈 Router loading summary: {loaded_count}/{total_count} routers loaded successfully")

# ===== VERCELL HANDLER =====
from mangum import Mangum
handler = Mangum(app)

logger.info("🏁 Main.py setup completed")