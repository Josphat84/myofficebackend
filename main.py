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

# Import and include routers with comprehensive error handling
logger.info("🔄 Starting router imports...")

try:
    from app.routers import (
        equipment, employees, reports, maintenance, inventory, overtime, 
        standby, ppe, leave, noticeboard, documents, training, visualization 
    )
    logger.info("✅ All routers imported successfully")
    
    # Log each router's details
    routers = [
        ("equipment", equipment.router, "/api/equipment"),
        ("employees", employees.router, "/api/employees"),
        ("reports", reports.router, "/api/reports"),
        ("maintenance", maintenance.router, "/api/maintenance"),
        ("inventory", inventory.router, "/api/inventory"),
        ("overtime", overtime.router, "/api/overtime"),
        ("standby", standby.router, "/api/standby"),
        ("ppe", ppe.router, "/api/ppe"),
        ("leave", leave.router, "/api/leave"),
    ]
    
    for name, router, prefix in routers:
        try:
            app.include_router(router, prefix=prefix, tags=[name.title()])
            logger.info(f"✅ {name.title()} router included at {prefix}")
            logger.info(f"   - Routes: {len(router.routes)}")
            for route in router.routes:
                if hasattr(route, 'methods') and hasattr(route, 'path'):
                    logger.info(f"     {list(route.methods)} {prefix}{route.path}")
        except Exception as e:
            logger.error(f"❌ Failed to include {name} router: {e}")
            logger.error(traceback.format_exc())
    
    # Include routers without additional prefix
    no_prefix_routers = [
        ("noticeboard", noticeboard.router),
        ("documents", documents.router),
        ("training", training.router),
        ("visualization", visualization.router),
    ]
    
    for name, router in no_prefix_routers:
        try:
            app.include_router(router, tags=[name.title()])
            logger.info(f"✅ {name.title()} router included (no additional prefix)")
            logger.info(f"   - Routes: {len(router.routes)}")
            for route in router.routes:
                if hasattr(route, 'methods') and hasattr(route, 'path'):
                    logger.info(f"     {list(route.methods)} {route.path}")
        except Exception as e:
            logger.error(f"❌ Failed to include {name} router: {e}")
            logger.error(traceback.format_exc())
    
    logger.info("🎉 All routers included successfully!")
    
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error(traceback.format_exc())
except Exception as e:
    logger.error(f"❌ Unexpected error during router setup: {e}")
    logger.error(traceback.format_exc())

# Debug: List all registered routes
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Application starting up...")
    logger.info("📋 Registered routes:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            logger.info(f"   {methods} {route.path}")

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

# Debug: Test Supabase connection
@app.get("/api/debug-supabase")
async def debug_supabase():
    logger.info("🔧 Supabase debug endpoint called")
    try:
        from app.supabase_client import supabase
        # Test a simple query
        result = supabase.table("employees").select("count", count="exact").execute()
        logger.info(f"✅ Supabase connection test: {result}")
        return {
            "status": "success",
            "message": "Supabase connection working",
            "employee_count": result.count if hasattr(result, 'count') else "unknown"
        }
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
        return {
            "status": "error",
            "message": f"Supabase connection failed: {str(e)}"
        }

# Vercel handler
from mangum import Mangum
handler = Mangum(app)

logger.info("🏁 Main.py setup completed")