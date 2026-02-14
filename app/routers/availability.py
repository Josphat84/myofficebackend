from fastapi import APIRouter, HTTPException
import logging
from app.supabase_client import supabase
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/availabilities")
async def get_availabilities():
    """Get equipment with their latest availability data"""
    try:
        logger.info("Fetching equipment with availability data...")
        
        # Get all equipment
        equipment_response = supabase.table("equipment").select("*").execute()
        equipment = equipment_response.data if hasattr(equipment_response, 'data') else equipment_response
        
        # For each equipment, get latest availability data
        for eq in equipment:
            # Get latest availability record for this equipment
            availability_response = supabase.table("availabilities") \
                .select("*") \
                .eq("equipment_id", eq["id"]) \
                .order("date", desc=True) \
                .limit(1) \
                .execute()
            
            if availability_response.data:
                latest = availability_response.data[0]
                eq["availability"] = latest["availability_percentage"]
                eq["operational_hours"] = latest["operational_hours"]
                eq["breakdown_hours"] = latest["breakdown_hours"]
                eq["status"] = latest["status"]
                eq["uptime"] = latest["operational_hours"] - latest["breakdown_hours"]
                eq["downtime"] = latest["breakdown_hours"]
                eq["mtbf"] = latest.get("mtbf", 100)
                eq["mttr"] = latest.get("mttr", 4)
                eq["last_maintenance"] = latest.get("date")
            else:
                # Default values if no availability data
                eq["availability"] = 100.00
                eq["operational_hours"] = eq.get("operational_hours", 0)
                eq["breakdown_hours"] = eq.get("breakdown_hours", 0)
                eq["status"] = eq.get("status", "operational")
                eq["uptime"] = eq.get("operational_hours", 0) - eq.get("breakdown_hours", 0)
                eq["downtime"] = eq.get("breakdown_hours", 0)
                eq["mtbf"] = 100
                eq["mttr"] = 4
                eq["last_maintenance"] = eq.get("last_maintenance_date")
        
        return equipment
        
    except Exception as e:
        logger.error(f"Error fetching availabilities: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching availabilities: {str(e)}")

@router.get("/availabilities/stats")
async def get_availability_stats():
    """Get availability statistics from the availabilities table"""
    try:
        logger.info("Calculating availability statistics...")
        
        # Get data from last 30 days
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Get aggregated stats from availabilities table
        stats_response = supabase.rpc('get_availability_stats', {
            'start_date': thirty_days_ago
        }).execute()
        
        if stats_response.data:
            return stats_response.data[0]
        
        # Fallback: Calculate manually
        equipment_response = supabase.table("equipment").select("*").execute()
        equipment = equipment_response.data if hasattr(equipment_response, 'data') else equipment_response
        
        if not equipment:
            return {
                "totalEquipment": 0,
                "operational": 0,
                "inMaintenance": 0,
                "inBreakdown": 0,
                "overallAvailability": 0,
                "avgUptime": 0,
                "avgDowntime": 0,
                "totalOperationalHours": 0,
                "totalBreakdownHours": 0,
                "monthAvailability": 0,
                "weekAvailability": 0
            }
        
        # Calculate from equipment table
        total_equipment = len(equipment)
        operational = sum(1 for eq in equipment if eq.get("status") == "operational")
        in_maintenance = sum(1 for eq in equipment if eq.get("status") == "maintenance")
        in_breakdown = sum(1 for eq in equipment if eq.get("status") == "breakdown")
        
        total_operational_hours = sum(eq.get("operational_hours", 0) or 0 for eq in equipment)
        total_breakdown_hours = sum(eq.get("breakdown_hours", 0) or 0 for eq in equipment)
        
        if total_operational_hours > 0:
            overall_availability = ((total_operational_hours - total_breakdown_hours) / total_operational_hours) * 100
        else:
            overall_availability = 0
            
        return {
            "totalEquipment": total_equipment,
            "operational": operational,
            "inMaintenance": in_maintenance,
            "inBreakdown": in_breakdown,
            "overallAvailability": round(overall_availability, 2),
            "avgUptime": round((total_operational_hours - total_breakdown_hours) / total_equipment, 2),
            "avgDowntime": round(total_breakdown_hours / total_equipment, 2),
            "totalOperationalHours": round(total_operational_hours, 2),
            "totalBreakdownHours": round(total_breakdown_hours, 2),
            "monthAvailability": round(overall_availability, 2),
            "weekAvailability": round(overall_availability * 0.98, 2)
        }
        
    except Exception as e:
        logger.error(f"Error calculating stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")

@router.get("/availabilities/history/{equipment_id}")
async def get_availability_history(equipment_id: int, days: int = 30):
    """Get availability history for specific equipment"""
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        response = supabase.table("availabilities") \
            .select("*") \
            .eq("equipment_id", equipment_id) \
            .gte("date", start_date) \
            .order("date", desc=True) \
            .execute()
        
        return response.data if hasattr(response, 'data') else response
        
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")
    