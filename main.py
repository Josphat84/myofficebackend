# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# Debug: Test if main router works
@app.get("/api/debug-test")
async def debug_test():
    logger.info("🔧 Debug test endpoint called")
    return {"message": "Debug test - main router working", "status": "success"}

# Debug: Test direct overtime route
@app.get("/api/debug-overtime-direct")
async def debug_overtime_direct():
    logger.info("🔧 Direct overtime debug endpoint called")
    return {"message": "Direct overtime debug - working", "router": "main"}

# Debug: Check if overtime router loads
@app.get("/api/debug-overtime-router")
async def debug_overtime_router():
    try:
        from app.routers import overtime
        routes = []
        for route in overtime.router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                routes.append({
                    'methods': list(route.methods),
                    'path': route.path
                })
        return {
            "status": "loaded",
            "router_routes": routes,
            "total_routes": len(routes)
        }
    except Exception as e:
        return {
            "status": "failed", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# Import and include routers with comprehensive error handling
logger.info("🔄 Starting router imports...")

# CRITICAL FIX: Import each router individually with error handling
routers_to_import = [
    "equipment", "employees", "reports", "maintenance", "inventory", 
    "overtime", "standby", "ppe", "leave", "noticeboard", "documents", 
    "training", "visualization"
]

loaded_routers = {}

for router_name in routers_to_import:
    try:
        module = __import__(f"app.routers.{router_name}", fromlist=[router_name])
        router_obj = getattr(module, 'router')
        loaded_routers[router_name] = router_obj
        logger.info(f"✅ {router_name.title()} router imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import {router_name} router: {e}")
        logger.error(traceback.format_exc())

# Now include the successfully loaded routers
try:
    # Routers with prefix
    prefixed_routers = [
        ("equipment", loaded_routers.get("equipment"), "/api/equipment"),
        ("employees", loaded_routers.get("employees"), "/api/employees"),
        ("reports", loaded_routers.get("reports"), "/api/reports"),
        ("maintenance", loaded_routers.get("maintenance"), "/api/maintenance"),
        ("inventory", loaded_routers.get("inventory"), "/api/inventory"),
        ("overtime", loaded_routers.get("overtime"), "/api/overtime"),  # THIS IS CRITICAL
        ("standby", loaded_routers.get("standby"), "/api/standby"),
        ("ppe", loaded_routers.get("ppe"), "/api/ppe"),
        ("leave", loaded_routers.get("leave"), "/api/leave"),
    ]
    
    for name, router, prefix in prefixed_routers:
        if router:
            try:
                app.include_router(router, prefix=prefix, tags=[name.title()])
                logger.info(f"✅ {name.title()} router included at {prefix}")
                logger.info(f"   - Routes: {len(router.routes)}")
            except Exception as e:
                logger.error(f"❌ Failed to include {name} router: {e}")
        else:
            logger.error(f"❌ {name.title()} router not available for inclusion")
    
    # Include routers without additional prefix
    no_prefix_routers = [
        ("noticeboard", loaded_routers.get("noticeboard")),
        ("documents", loaded_routers.get("documents")),
        ("training", loaded_routers.get("training")),
        ("visualization", loaded_routers.get("visualization")),
    ]
    
    for name, router in no_prefix_routers:
        if router:
            try:
                app.include_router(router, tags=[name.title()])
                logger.info(f"✅ {name.title()} router included (no additional prefix)")
            except Exception as e:
                logger.error(f"❌ Failed to include {name} router: {e}")
        else:
            logger.error(f"❌ {name.title()} router not available for inclusion")
    
    logger.info("🎉 Router inclusion completed!")
    
except Exception as e:
    logger.error(f"❌ Error during router inclusion: {e}")
    logger.error(traceback.format_exc())

# Debug: List all registered routes
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Application starting up...")
    logger.info("📋 Registered routes:")
    overtime_routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            path_info = f"   {methods} {route.path}"
            logger.info(path_info)
            if '/api/overtime' in str(route.path):
                overtime_routes.append(path_info)
    
    if overtime_routes:
        logger.info("🎯 Overtime routes found:")
        for route in overtime_routes:
            logger.info(route)
    else:
        logger.error("❌ No overtime routes found!")

@app.get("/", tags=["Root"])
async def root():
    logger.info("🌐 Root endpoint called")
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
            "noticeboard": "/api/notices",
            "training": "/api/training",
            "visualization": "/api/viz",
            
            # --- DEBUG ENDPOINTS ---
            "debug_test": "/api/debug-test",
            "debug_overtime": "/api/debug-overtime-direct",
            "debug_overtime_router": "/api/debug-overtime-router",
            "health": "/api/health",
            "docs": "/docs"
        }
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    logger.info("❤️ Health check called")
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

logger.info("🏁 Main.py setup completed")