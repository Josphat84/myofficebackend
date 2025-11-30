# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import traceback
import os

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

# ===== BASIC ENDPOINTS THAT SHOULD ALWAYS WORK =====
@app.get("/")
async def root():
    return {
        "message": "MyOffice API is running!",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "docs": "/docs"
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

# ===== ROUTER IMPORTS AND INCLUSION =====
logger.info("🔄 Starting router imports...")

# Updated routers list - removed work_orders and job_cards since they're now in maintenance
# ADDED 'sheq' to the routers list
routers_to_import = [
    "equipment", "employees", "reports", "inventory", 
    "overtime", "standby", "ppe", "noticeboard", "documents", 
    "training", "visualization", "leaves", "sheq"  # Removed maintenance from here since we'll import it separately
]

loaded_routers = {}

for router_name in routers_to_import:
    try:
        module = __import__(f"app.routers.{router_name}", fromlist=[router_name])
        router_obj = getattr(module, 'router')
        loaded_routers[router_name] = router_obj
        
        # Include router immediately with proper prefix
        prefix = f"/api/{router_name.replace('_', '-')}"
        app.include_router(router_obj, prefix=prefix, tags=[router_name.title()])
        logger.info(f"✅ {router_name.title()} router included at {prefix}")
        
    except Exception as e:
        logger.error(f"❌ Failed to import {router_name} router: {e}")
        logger.error(traceback.format_exc())

# ===== MANUALLY INCLUDE THE SELF-CONTAINED MAINTENANCE ROUTER =====
try:
    # Import the self-contained maintenance router from the routers directory
    from app.routers.maintenance import router as maintenance_router
    # Include it at the /api/maintenance prefix since it contains all maintenance-related endpoints
    app.include_router(maintenance_router, prefix="/api/maintenance", tags=["Maintenance"])
    loaded_routers["maintenance"] = maintenance_router
    logger.info("✅ Self-contained Maintenance router included at /api/maintenance")
    
except Exception as e:
    logger.error(f"❌ Failed to import self-contained maintenance router: {e}")
    logger.error(traceback.format_exc())

# ===== DEBUG ENDPOINTS (DEFINED AFTER ROUTERS) =====
@app.get("/api/debug-overtime-status")
async def debug_overtime_status():
    """Check if overtime routes are available"""
    try:
        # Check if we have the overtime router
        overtime_router = loaded_routers.get("overtime")
        
        if not overtime_router:
            return {
                "status": "missing",
                "message": "Overtime router not loaded",
                "loaded_routers": list(loaded_routers.keys()),
                "fallback_endpoints": [
                    "GET /api/overtime",
                    "GET /api/overtime/stats", 
                    "GET /api/overtime/balance/{employee_id}"
                ]
            }
        
        # Check routes in the overtime router
        overtime_routes = []
        for route in overtime_router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                overtime_routes.append({
                    'methods': list(route.methods),
                    'path': str(route.path)
                })
        
        return {
            "status": "loaded",
            "overtime_routes": overtime_routes,
            "total_overtime_routes": len(overtime_routes)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Overtime router not functioning properly"
        }

@app.get("/api/debug-work-orders-status")
async def debug_work_orders_status():
    """Check if work_orders routes are available via maintenance router"""
    try:
        # Check if we have the maintenance router
        maintenance_router = loaded_routers.get("maintenance")
        
        if not maintenance_router:
            return {
                "status": "missing",
                "message": "Maintenance router not loaded",
                "loaded_routers": list(loaded_routers.keys())
            }
        
        # Check routes in the maintenance router for work-orders endpoints
        work_order_routes = []
        for route in maintenance_router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                path_str = str(route.path)
                if 'work-orders' in path_str:
                    work_order_routes.append({
                        'methods': list(route.methods),
                        'path': path_str
                    })
        
        return {
            "status": "loaded" if work_order_routes else "no_work_order_routes",
            "work_order_routes": work_order_routes,
            "total_work_order_routes": len(work_order_routes),
            "message": "Work orders are now part of the self-contained maintenance router at /api/maintenance/work-orders"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/debug-maintenance-status")
async def debug_maintenance_status():
    """Check maintenance router status and available endpoints"""
    try:
        maintenance_router = loaded_routers.get("maintenance")
        
        if not maintenance_router:
            return {
                "status": "missing",
                "message": "Maintenance router not loaded",
                "loaded_routers": list(loaded_routers.keys())
            }
        
        # Get all routes from maintenance router
        all_routes = []
        work_order_routes = []
        ppe_routes = []
        dashboard_routes = []
        
        for route in maintenance_router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                route_info = {
                    'methods': list(route.methods),
                    'path': str(route.path)
                }
                all_routes.append(route_info)
                
                path_str = str(route.path)
                if 'work-orders' in path_str:
                    work_order_routes.append(route_info)
                elif 'ppe' in path_str:
                    ppe_routes.append(route_info)
                elif 'dashboard' in path_str:
                    dashboard_routes.append(route_info)
        
        return {
            "status": "loaded",
            "total_routes": len(all_routes),
            "work_order_routes_count": len(work_order_routes),
            "ppe_routes_count": len(ppe_routes),
            "dashboard_routes_count": len(dashboard_routes),
            "available_endpoints": {
                "work_orders": work_order_routes,
                "ppe": ppe_routes,
                "dashboard": dashboard_routes
            },
            "access_note": "All endpoints are under /api/maintenance prefix (e.g., /api/maintenance/work-orders)"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/debug-leaves-status")
async def debug_leaves_status():
    """Check if leaves router is loaded"""
    try:
        leaves_router = loaded_routers.get("leaves")
        
        if not leaves_router:
            return {
                "status": "missing",
                "message": "Leaves router not loaded",
                "loaded_routers": list(loaded_routers.keys())
            }
        
        # Check routes in the router
        routes = []
        for route in leaves_router.routes:
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
            "status": "error",
            "error": str(e)
        }

# ===== NEW DEBUG ENDPOINT FOR SHEQ =====
@app.get("/api/debug-sheq-status")
async def debug_sheq_status():
    """Check if SHEQ router is loaded"""
    try:
        sheq_router = loaded_routers.get("sheq")
        
        if not sheq_router:
            return {
                "status": "missing",
                "message": "SHEQ router not loaded",
                "loaded_routers": list(loaded_routers.keys())
            }
        
        # Check routes in the router
        routes = []
        for route in sheq_router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                routes.append({
                    'methods': list(route.methods),
                    'path': route.path
                })
        
        return {
            "status": "loaded",
            "router_routes": routes,
            "total_routes": len(routes),
            "expected_endpoints": [
                "GET /api/sheq - Get all SHEQ reports with filtering",
                "POST /api/sheq - Create new SHEQ report",
                "GET /api/sheq/{report_id} - Get specific SHEQ report",
                "PATCH /api/sheq/{report_id} - Update SHEQ report",
                "DELETE /api/sheq/{report_id} - Delete SHEQ report",
                "GET /api/sheq/stats/summary - Get SHEQ statistics"
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
    
    work_order_routes = [r for r in routes if 'work-orders' in r['path']]
    maintenance_routes = [r for r in routes if 'maintenance' in r['path'] and 'work-orders' not in r['path']]
    leaves_routes = [r for r in routes if 'leaves' in r['path']]
    overtime_routes = [r for r in routes if 'overtime' in r['path']]
    sheq_routes = [r for r in routes if 'sheq' in r['path']]  # Added SHEQ routes
    
    return {
        "all_routes": routes,
        "work_order_routes": work_order_routes,
        "maintenance_routes": maintenance_routes,
        "leaves_routes": leaves_routes,
        "overtime_routes": overtime_routes,
        "sheq_routes": sheq_routes,  # Added SHEQ routes
        "total_routes": len(routes),
        "total_work_order_routes": len(work_order_routes),
        "total_maintenance_routes": len(maintenance_routes),
        "total_leaves_routes": len(leaves_routes),
        "total_overtime_routes": len(overtime_routes),
        "total_sheq_routes": len(sheq_routes)  # Added SHEQ count
    }

@app.get("/api/debug-router-imports")
async def debug_router_imports():
    """Show which routers imported successfully"""
    return {
        "routers_to_import": routers_to_import,
        "loaded_routers": list(loaded_routers.keys()),
        "missing_routers": [r for r in routers_to_import if r not in loaded_routers],
        "note": "work_orders and job_cards are now part of the self-contained maintenance router at /api/maintenance"
    }

# ===== OVERTIME TEST ENDPOINT (RENAMED TO AVOID CONFLICT) =====
@app.get("/api/overtime-test")
async def overtime_test():
    """Test overtime endpoint with sample data - renamed to avoid conflict with actual routes"""
    return {
        "status": "success",
        "message": "Overtime API is working!",
        "test_data": {
            "employee_name": "Test Employee",
            "employee_id": "TEST001",
            "position": "Test Position",
            "overtime_type": "regular",
            "date": "2024-01-15",
            "start_time": "17:00",
            "end_time": "20:00",
            "reason": "Test overtime application",
            "contact_number": "+263 77 123 4567",
            "hourly_rate": 25.0,
            "status": "pending"
        }
    }

# ===== MAINTENANCE SPECIFIC DEBUG ENDPOINTS =====
@app.get("/api/debug-maintenance-test")
async def debug_maintenance_test():
    """Test maintenance endpoints"""
    try:
        # Test data for work orders
        test_work_order_data = {
            "title": "Test Work Order from Maintenance Router",
            "description": "Test work order description from self-contained router",
            "status": "pending",
            "priority": "medium",
            "allocated_to": "Test Technician",
            "to_department": "Test Department",
            "equipment_info": "Test Equipment",
            "requested_by": "Test Requester",
            "date_raised": "2024-01-15",
            "time_raised": "10:00",
            "estimated_hours": 4.5,
            "progress": 0,
            "cost_estimate": 500.00,
            "safety_level": "medium",
            "location": "Test Location",
            "due_date": "2024-01-25"
        }
        
        return {
            "status": "maintenance_router_available",
            "test_data": test_work_order_data,
            "endpoints_available": [
                "GET /api/maintenance/work-orders - Get all work orders",
                "POST /api/maintenance/work-orders - Create work order",
                "GET /api/maintenance/work-orders/{id} - Get specific work order",
                "PATCH /api/maintenance/work-orders/{id} - Update work order",
                "DELETE /api/maintenance/work-orders/{id} - Delete work order",
                "GET /api/maintenance/work-orders/stats/summary - Get work order statistics",
                "GET /api/maintenance/work-orders/allocated/{allocated_to} - Get work orders by allocated person",
                "GET /api/maintenance/dashboard/stats - Get combined maintenance dashboard stats"
            ],
            "note": "This uses the new self-contained maintenance router with integrated database and models"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ===== LEAVES SPECIFIC DEBUG ENDPOINTS =====
@app.get("/api/debug-leaves-test")
async def debug_leaves_test():
    """Test leaves endpoints without authentication"""
    try:
        # Test data for leaves that matches our LeaveCreate model
        test_leave_data = {
            "employee_name": "Test Employee",
            "employee_id": "TEST001",
            "position": "Test Position",
            "leave_type": "annual",
            "start_date": "2024-02-01",
            "end_date": "2024-02-05",
            "reason": "Test leave application",
            "contact_number": "+263 77 123 4567",
            "emergency_contact": "Test Contact +263 77 987 6543",
            "handover_to": "Test Colleague"
        }
        
        return {
            "status": "leaves_router_available",
            "test_data": test_leave_data,
            "endpoints_available": [
                "POST /api/leaves/ - Create leave application",
                "GET /api/leaves/ - Get all leaves (with optional status and leave_type filters)",
                "GET /api/leaves/{leave_id} - Get specific leave",
                "PATCH /api/leaves/{leave_id} - Update leave status",
                "DELETE /api/leaves/{leave_id} - Delete leave",
                "GET /api/leaves/stats/summary - Get leave statistics",
                "GET /api/leaves/balance/{employee_id} - Get leave balance",
                "GET /api/leaves/search/{search_term} - Search leaves",
                "GET /api/leaves/health/status - Health check"
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ===== SHEQ SPECIFIC DEBUG ENDPOINTS =====
@app.get("/api/debug-sheq-test")
async def debug_sheq_test():
    """Test SHEQ endpoints"""
    try:
        # Test data for SHEQ reports
        test_sheq_data = {
            "report_type": "hazard",
            "employee_name": "Test Employee",
            "employee_id": "TEST001",
            "department": "MAINTENANCE",
            "position": "Technician",
            "location": "Workshop",
            "priority": "high",
            "status": "open",
            "hazard_description": "Exposed electrical wiring in workshop area",
            "risk_assessment": "High risk of electrical shock",
            "suggested_improvements": "Install proper conduit and warning signs",
            "corrective_actions": "Electrician to secure wiring immediately",
            "responsible_person": "Maintenance Supervisor",
            "due_date": "2024-01-20"
        }
        
        return {
            "status": "sheq_router_available",
            "test_data": test_sheq_data,
            "endpoints_available": [
                "GET /api/sheq - Get all SHEQ reports with filtering",
                "POST /api/sheq - Create new SHEQ report",
                "GET /api/sheq/{report_id} - Get specific SHEQ report",
                "PATCH /api/sheq/{report_id} - Update SHEQ report",
                "DELETE /api/sheq/{report_id} - Delete SHEQ report",
                "GET /api/sheq/stats/summary - Get SHEQ statistics"
            ],
            "supported_report_types": ["hazard", "near_miss", "incident", "pto"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ===== HEALTH CHECK ENDPOINTS =====
@app.get("/api/leaves/health")
async def leaves_health_check():
    """Quick health check for leaves service"""
    try:
        leaves_router = loaded_routers.get("leaves")
        if leaves_router:
            return {
                "status": "healthy",
                "service": "leaves",
                "message": "Leaves router is loaded and ready"
            }
        else:
            return {
                "status": "unhealthy", 
                "service": "leaves",
                "message": "Leaves router not found"
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "leaves",
            "error": str(e)
        }

@app.get("/api/overtime/health")
async def overtime_health_check():
    """Quick health check for overtime service"""
    try:
        overtime_router = loaded_routers.get("overtime")
        if overtime_router:
            return {
                "status": "healthy",
                "service": "overtime",
                "message": "Overtime router is loaded and ready"
            }
        else:
            return {
                "status": "unhealthy", 
                "service": "overtime",
                "message": "Overtime router not found"
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "overtime",
            "error": str(e)
        }

@app.get("/api/sheq/health")
async def sheq_health_check():
    """Quick health check for SHEQ service"""
    try:
        sheq_router = loaded_routers.get("sheq")
        if sheq_router:
            return {
                "status": "healthy",
                "service": "sheq",
                "message": "SHEQ router is loaded and ready"
            }
        else:
            return {
                "status": "unhealthy", 
                "service": "sheq",
                "message": "SHEQ router not found"
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "sheq",
            "error": str(e)
        }

@app.get("/api/maintenance/health")
async def maintenance_health_check():
    """Quick health check for maintenance service"""
    try:
        maintenance_router = loaded_routers.get("maintenance")
        if maintenance_router:
            return {
                "status": "healthy",
                "service": "maintenance",
                "message": "Maintenance router is loaded and ready",
                "endpoints_available": [
                    "/api/maintenance/work-orders",
                    "/api/maintenance/work-orders/stats/summary",
                    "/api/maintenance/dashboard/stats"
                ]
            }
        else:
            return {
                "status": "unhealthy", 
                "service": "maintenance",
                "message": "Maintenance router not found"
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "maintenance",
            "error": str(e)
        }

# ===== STARTUP EVENT =====
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Application starting up...")
    
    # Log all routes
    logger.info("📋 Registered routes:")
    work_orders_routes = []
    maintenance_routes = []
    leaves_routes = []
    overtime_routes = []
    sheq_routes = []  # Added SHEQ routes
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods) if hasattr(route, 'methods') else []
            path_info = f"   {methods} {route.path}"
            
            if '/api/maintenance/work-orders' in str(route.path):
                work_orders_routes.append(path_info)
            elif '/api/maintenance' in str(route.path) and '/api/maintenance/work-orders' not in str(route.path):
                maintenance_routes.append(path_info)
            elif '/api/leaves' in str(route.path):
                leaves_routes.append(path_info)
            elif '/api/overtime' in str(route.path):
                overtime_routes.append(path_info)
            elif '/api/sheq' in str(route.path):  # Added SHEQ routes
                sheq_routes.append(path_info)
    
    if work_orders_routes:
        logger.info("📝 Work Orders routes found (under /api/maintenance):")
        for route in work_orders_routes:
            logger.info(route)
    else:
        logger.warning("⚠️ No work orders routes found!")
    
    if maintenance_routes:
        logger.info("🔧 Maintenance routes found:")
        for route in maintenance_routes:
            logger.info(route)
    else:
        logger.warning("⚠️ No maintenance routes found!")
    
    if leaves_routes:
        logger.info("🍃 Leaves routes found:")
        for route in leaves_routes:
            logger.info(route)
    else:
        logger.warning("⚠️ No leaves routes found!")
    
    if overtime_routes:
        logger.info("⏰ Overtime routes found:")
        for route in overtime_routes:
            logger.info(route)
    else:
        logger.warning("⚠️ No overtime routes found!")
    
    if sheq_routes:  # Added SHEQ routes logging
        logger.info("🛡️ SHEQ routes found:")
        for route in sheq_routes:
            logger.info(route)
    else:
        logger.warning("⚠️ No SHEQ routes found!")

# ===== VERCELL HANDLER =====
from mangum import Mangum
handler = Mangum(app)

logger.info("🏁 Main.py setup completed")