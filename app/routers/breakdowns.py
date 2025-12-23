from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date, timedelta, time
import json
import logging
import csv
import io
from supabase import create_client, Client
import os
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Breakdown Management API",
    version="2.0.0",
    description="Advanced breakdown tracking with time calculations and reporting"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "your-anon-key")

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase client initialized successfully")
except Exception as e:
    logger.error(f"❌ Error initializing Supabase client: {e}")
    supabase = None

# Pydantic Models
class SparePart(BaseModel):
    name: str = Field(..., min_length=1)
    quantity: int = Field(1, ge=1)
    part_number: Optional[str] = None
    unit_price: Optional[float] = Field(0.0, ge=0.0)
    total_cost: Optional[float] = Field(0.0, ge=0.0)

    @validator('total_cost', always=True)
    def calculate_total_cost(cls, v, values):
        if 'quantity' in values and 'unit_price' in values:
            quantity = values.get('quantity', 1)
            unit_price = values.get('unit_price', 0.0)
            return round(quantity * unit_price, 2)
        return v or 0.0

class BreakdownCreate(BaseModel):
    artisan_name: str = Field(..., min_length=1)
    date: date
    machine_id: str = Field(..., min_length=1)
    machine_name: str = Field(..., min_length=1)
    machine_description: str = Field(..., min_length=5)
    location: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    breakdown_type: str = Field(..., min_length=1)
    breakdown_description: str = Field(..., min_length=10)
    root_cause: Optional[str] = None
    immediate_cause: Optional[str] = None
    work_done: str = Field(..., min_length=10)
    
    # Time fields (HH:MM format)
    breakdown_start: Optional[str] = None
    breakdown_end: Optional[str] = None
    work_start: Optional[str] = None
    work_end: Optional[str] = None
    delay_start: Optional[str] = None
    delay_end: Optional[str] = None
    
    delay_reason: Optional[str] = None
    spares_used: List[SparePart] = []
    artisan_recommendations: str = Field(..., min_length=10)
    foreman_comments: Optional[str] = None
    supervisor_comments: Optional[str] = None
    status: str = Field(default="logged")
    priority: str = Field(default="medium")
    
    # Calculated fields (will be computed)
    response_time_minutes: Optional[int] = None
    repair_time_minutes: Optional[int] = None
    delay_time_minutes: Optional[int] = None
    downtime_minutes: Optional[int] = None
    response_time_hours: Optional[float] = None
    repair_time_hours: Optional[float] = None
    delay_time_hours: Optional[float] = None
    downtime_hours: Optional[float] = None
    total_spare_cost: Optional[float] = None

    @validator(
        'breakdown_start', 'breakdown_end', 'work_start', 'work_end',
        'delay_start', 'delay_end', pre=True
    )
    def validate_time_format(cls, v):
        if v and v != "":
            try:
                # Validate HH:MM format
                if len(v) != 5 or v[2] != ':':
                    raise ValueError("Time must be in HH:MM format")
                hours, minutes = map(int, v.split(':'))
                if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                    raise ValueError("Invalid time values")
            except ValueError as e:
                raise ValueError(f"Invalid time format: {v}. Use HH:MM format. Error: {e}")
        return v

class BreakdownUpdate(BaseModel):
    artisan_name: Optional[str] = None
    date: Optional[date] = None
    machine_id: Optional[str] = None
    machine_name: Optional[str] = None
    machine_description: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    breakdown_type: Optional[str] = None
    breakdown_description: Optional[str] = None
    root_cause: Optional[str] = None
    immediate_cause: Optional[str] = None
    work_done: Optional[str] = None
    
    # Time fields
    breakdown_start: Optional[str] = None
    breakdown_end: Optional[str] = None
    work_start: Optional[str] = None
    work_end: Optional[str] = None
    delay_start: Optional[str] = None
    delay_end: Optional[str] = None
    
    delay_reason: Optional[str] = None
    spares_used: Optional[List[SparePart]] = None
    artisan_recommendations: Optional[str] = None
    foreman_comments: Optional[str] = None
    supervisor_comments: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    
    # Calculated fields
    response_time_minutes: Optional[int] = None
    repair_time_minutes: Optional[int] = None
    delay_time_minutes: Optional[int] = None
    downtime_minutes: Optional[int] = None
    response_time_hours: Optional[float] = None
    repair_time_hours: Optional[float] = None
    delay_time_hours: Optional[float] = None
    downtime_hours: Optional[float] = None
    total_spare_cost: Optional[float] = None

# Helper Functions
def time_to_minutes(time_str: str) -> int:
    """Convert HH:MM time string to minutes"""
    if not time_str:
        return 0
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    except:
        return 0

def minutes_to_hours_decimal(minutes: int) -> float:
    """Convert minutes to decimal hours"""
    if not minutes:
        return 0.0
    return round(minutes / 60, 2)

def calculate_time_metrics(breakdown_data: dict) -> dict:
    """Calculate all time-based metrics with enhanced calculations"""
    try:
        # Get times
        b_start = time_to_minutes(breakdown_data.get('breakdown_start'))
        b_end = time_to_minutes(breakdown_data.get('breakdown_end'))
        w_start = time_to_minutes(breakdown_data.get('work_start'))
        w_end = time_to_minutes(breakdown_data.get('work_end'))
        d_start = time_to_minutes(breakdown_data.get('delay_start'))
        d_end = time_to_minutes(breakdown_data.get('delay_end'))
        
        # Calculate metrics
        response_time = max(0, w_start - b_start) if b_start and w_start else 0
        repair_time = max(0, w_end - w_start) if w_start and w_end else 0
        delay_time = max(0, d_end - d_start) if d_start and d_end else 0
        
        # Downtime: Breakdown end - Breakdown start (including delays)
        if b_start and b_end:
            downtime = max(0, b_end - b_start)
        else:
            downtime = 0
        
        # Net downtime: Downtime - Delay time
        net_downtime = max(0, downtime - delay_time) if downtime and delay_time else downtime
        
        return {
            "response_time_minutes": response_time,
            "repair_time_minutes": repair_time,
            "delay_time_minutes": delay_time,
            "downtime_minutes": downtime,
            "net_downtime_minutes": net_downtime,
            "response_time_hours": minutes_to_hours_decimal(response_time),
            "repair_time_hours": minutes_to_hours_decimal(repair_time),
            "delay_time_hours": minutes_to_hours_decimal(delay_time),
            "downtime_hours": minutes_to_hours_decimal(downtime),
            "net_downtime_hours": minutes_to_hours_decimal(net_downtime)
        }
    except Exception as e:
        logger.error(f"Error calculating time metrics: {e}")
        return {
            "response_time_minutes": 0,
            "repair_time_minutes": 0,
            "delay_time_minutes": 0,
            "downtime_minutes": 0,
            "net_downtime_minutes": 0,
            "response_time_hours": 0.0,
            "repair_time_hours": 0.0,
            "delay_time_hours": 0.0,
            "downtime_hours": 0.0,
            "net_downtime_hours": 0.0
        }

def calculate_spare_costs(spares: List[SparePart]) -> dict:
    """Calculate spare part costs with detailed breakdown"""
    try:
        total_cost = 0.0
        spares_with_costs = []
        
        for spare in spares:
            spare_dict = spare.dict()
            # Ensure costs are calculated
            if spare_dict.get('total_cost') is None:
                quantity = spare_dict.get('quantity', 1)
                unit_price = spare_dict.get('unit_price', 0.0)
                spare_dict['total_cost'] = round(quantity * unit_price, 2)
            
            total_cost += spare_dict['total_cost']
            spares_with_costs.append(spare_dict)
        
        return {
            "total_spare_cost": round(total_cost, 2),
            "spares_used": spares_with_costs
        }
    except Exception as e:
        logger.error(f"Error calculating spare costs: {e}")
        return {"total_spare_cost": 0.0, "spares_used": []}

def convert_dates_to_iso(record: dict) -> dict:
    """Convert date objects to ISO format strings"""
    for key, value in record.items():
        if isinstance(value, (date, datetime)):
            record[key] = value.isoformat()
    return record

def format_time_display(minutes: int) -> dict:
    """Format time in minutes to various display formats"""
    if not minutes:
        return {
            "minutes": 0,
            "hours_decimal": 0.0,
            "display": "0m",
            "detailed": "0 minutes"
        }
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    hours_decimal = round(minutes / 60, 2)
    
    if hours > 0:
        display = f"{hours}h {remaining_minutes}m"
        detailed = f"{hours} hours {remaining_minutes} minutes"
    else:
        display = f"{minutes}m"
        detailed = f"{minutes} minutes"
    
    return {
        "minutes": minutes,
        "hours_decimal": hours_decimal,
        "display": display,
        "detailed": detailed
    }

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Breakdown Management API v2.0",
        "status": "active",
        "features": [
            "Time calculations with decimal hours",
            "Delay time tracking",
            "CSV/Excel report generation",
            "Advanced statistics",
            "Grid/List view support"
        ]
    }

@app.get("/api/breakdowns")
async def get_breakdowns(
    status: Optional[str] = Query(None),
    breakdown_type: Optional[str] = Query(None),
    machine_id: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    artisan_name: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    view_mode: Optional[str] = Query("list"),  # list or grid
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get breakdowns with optional filtering and view modes"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        query = supabase.table("breakdowns").select("*", count="exact")
        
        # Apply filters
        if status and status != "all":
            query = query.eq("status", status)
        if breakdown_type and breakdown_type != "all":
            query = query.eq("breakdown_type", breakdown_type)
        if machine_id and machine_id != "all":
            query = query.eq("machine_id", machine_id)
        if location and location != "all":
            query = query.eq("location", location)
        if department and department != "all":
            query = query.eq("department", department)
        if artisan_name and artisan_name != "all":
            query = query.ilike("artisan_name", f"%{artisan_name}%")
        if priority and priority != "all":
            query = query.eq("priority", priority)
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
        
        # Order and paginate
        if view_mode == "grid":
            # For grid view, get recent breakdowns first
            response = query.order("date", desc=True).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        else:
            # For list view, get all with standard ordering
            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Process records
        records = response.data or []
        for record in records:
            convert_dates_to_iso(record)
            
            # Parse spares_used if it's a string
            if isinstance(record.get('spares_used'), str):
                try:
                    record['spares_used'] = json.loads(record['spares_used'])
                except:
                    record['spares_used'] = []
            
            # Calculate time displays if not present
            if 'response_time_minutes' in record:
                record['response_time_display'] = format_time_display(record['response_time_minutes'])
                record['repair_time_display'] = format_time_display(record.get('repair_time_minutes', 0))
                record['downtime_display'] = format_time_display(record.get('downtime_minutes', 0))
                record['delay_time_display'] = format_time_display(record.get('delay_time_minutes', 0))
        
        return {
            "data": records,
            "count": len(records),
            "total": response.count if hasattr(response, 'count') else len(records),
            "view_mode": view_mode,
            "filters": {
                "status": status,
                "breakdown_type": breakdown_type,
                "machine_id": machine_id,
                "location": location,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching breakdowns: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching breakdowns: {str(e)}")

@app.post("/api/breakdowns")
async def create_breakdown(breakdown: BreakdownCreate):
    """Create a new breakdown record with automatic time calculations"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Prepare data for database
        data = breakdown.dict(exclude_unset=True)
        
        # Calculate time metrics
        time_metrics = calculate_time_metrics(data)
        data.update(time_metrics)
        
        # Calculate spare part costs
        if data.get('spares_used'):
            costs = calculate_spare_costs(breakdown.spares_used)
            data['total_spare_cost'] = costs['total_spare_cost']
            data['spares_used'] = json.dumps(costs['spares_used'])
        else:
            data['spares_used'] = '[]'
            data['total_spare_cost'] = 0.0
        
        # Convert date to string
        if data.get('date'):
            data['date'] = data['date'].isoformat()
        
        # Add timestamps
        now = datetime.utcnow().isoformat()
        data["created_at"] = now
        data["updated_at"] = now
        
        logger.info(f"Creating breakdown with data: {json.dumps(data, indent=2)}")
        
        # Insert into database
        response = supabase.table("breakdowns").insert(data).execute()
        
        if response.data:
            result = response.data[0]
            # Parse spares_used back to list
            if isinstance(result.get('spares_used'), str):
                try:
                    result['spares_used'] = json.loads(result['spares_used'])
                except:
                    result['spares_used'] = []
            
            # Add time displays
            if 'response_time_minutes' in result:
                result['response_time_display'] = format_time_display(result['response_time_minutes'])
                result['repair_time_display'] = format_time_display(result.get('repair_time_minutes', 0))
                result['downtime_display'] = format_time_display(result.get('downtime_minutes', 0))
                result['delay_time_display'] = format_time_display(result.get('delay_time_minutes', 0))
            
            convert_dates_to_iso(result)
            return result
        else:
            logger.error("No data returned from Supabase insert")
            raise HTTPException(status_code=500, detail="Failed to create breakdown record")
            
    except Exception as e:
        logger.error(f"Error creating breakdown record: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating breakdown record: {str(e)}")

@app.get("/api/breakdowns/{breakdown_id}")
async def get_breakdown(breakdown_id: int):
    """Get a specific breakdown by ID with enhanced details"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        response = supabase.table("breakdowns").select("*").eq("id", breakdown_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Breakdown record not found")
        
        result = response.data[0]
        
        # Parse spares_used
        if isinstance(result.get('spares_used'), str):
            try:
                result['spares_used'] = json.loads(result['spares_used'])
            except:
                result['spares_used'] = []
        
        # Add time displays
        if 'response_time_minutes' in result:
            result['response_time_display'] = format_time_display(result['response_time_minutes'])
            result['repair_time_display'] = format_time_display(result.get('repair_time_minutes', 0))
            result['downtime_display'] = format_time_display(result.get('downtime_minutes', 0))
            result['delay_time_display'] = format_time_display(result.get('delay_time_minutes', 0))
        
        # Calculate efficiency metrics
        if result.get('downtime_minutes') and result.get('repair_time_minutes'):
            downtime = result['downtime_minutes']
            repair_time = result['repair_time_minutes']
            if downtime > 0:
                result['efficiency_percentage'] = round((1 - (repair_time / downtime)) * 100, 2)
            else:
                result['efficiency_percentage'] = 100.0
        
        convert_dates_to_iso(result)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching breakdown record: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching breakdown record: {str(e)}")

@app.patch("/api/breakdowns/{breakdown_id}")
async def update_breakdown(breakdown_id: int, breakdown_update: BreakdownUpdate):
    """Update a breakdown record with recalculated metrics"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Check if record exists
        existing = supabase.table("breakdowns").select("*").eq("id", breakdown_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Breakdown record not found")
        
        # Prepare update data
        update_data = {k: v for k, v in breakdown_update.dict(exclude_unset=True).items() if v is not None}
        
        # Get existing record for time calculations
        existing_record = existing.data[0]
        
        # If time fields are being updated, recalculate all metrics
        time_fields = ['breakdown_start', 'breakdown_end', 'work_start', 'work_end', 'delay_start', 'delay_end']
        if any(key in update_data for key in time_fields):
            # Merge existing and updated time fields
            time_data = {}
            for field in time_fields:
                time_data[field] = update_data.get(field) or existing_record.get(field)
            
            times = calculate_time_metrics(time_data)
            update_data.update(times)
        
        # Handle spares_used update
        if 'spares_used' in update_data:
            if update_data['spares_used'] is not None:
                costs = calculate_spare_costs(update_data['spares_used'])
                update_data['total_spare_cost'] = costs['total_spare_cost']
                update_data['spares_used'] = json.dumps(costs['spares_used'])
            else:
                # Keep existing spares if None is provided
                update_data.pop('spares_used', None)
        
        # Handle date conversion
        if 'date' in update_data:
            update_data['date'] = update_data['date'].isoformat()
        
        # Add updated timestamp
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Perform update
        response = supabase.table("breakdowns").update(update_data).eq("id", breakdown_id).execute()
        
        if response.data:
            result = response.data[0]
            # Parse spares_used back to list
            if isinstance(result.get('spares_used'), str):
                try:
                    result['spares_used'] = json.loads(result['spares_used'])
                except:
                    result['spares_used'] = []
            
            # Add time displays
            if 'response_time_minutes' in result:
                result['response_time_display'] = format_time_display(result['response_time_minutes'])
                result['repair_time_display'] = format_time_display(result.get('repair_time_minutes', 0))
                result['downtime_display'] = format_time_display(result.get('downtime_minutes', 0))
                result['delay_time_display'] = format_time_display(result.get('delay_time_minutes', 0))
            
            convert_dates_to_iso(result)
            return result
        else:
            raise HTTPException(status_code=500, detail="Update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating breakdown record: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating breakdown record: {str(e)}")

@app.delete("/api/breakdowns/{breakdown_id}")
async def delete_breakdown(breakdown_id: int):
    """Delete a breakdown record"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Check if record exists
        existing = supabase.table("breakdowns").select("*").eq("id", breakdown_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Breakdown record not found")
        
        # Delete record
        supabase.table("breakdowns").delete().eq("id", breakdown_id).execute()
        
        return {"success": True, "message": "Breakdown record deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting breakdown record: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting breakdown record: {str(e)}")

@app.get("/api/breakdowns/export/csv")
async def export_breakdowns_csv(
    start_date: Optional[date] = Query(None, description="Start date for export"),
    end_date: Optional[date] = Query(None, description="End date for export"),
    status: Optional[str] = Query(None),
    breakdown_type: Optional[str] = Query(None),
    department: Optional[str] = Query(None)
):
    """Export breakdowns to CSV format"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Build query
        query = supabase.table("breakdowns").select("*")
        
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
        if status and status != "all":
            query = query.eq("status", status)
        if breakdown_type and breakdown_type != "all":
            query = query.eq("breakdown_type", breakdown_type)
        if department and department != "all":
            query = query.eq("department", department)
        
        response = query.order("date", desc=True).execute()
        records = response.data or []
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        headers = [
            "ID", "Date", "Machine ID", "Machine Name", "Location", "Department",
            "Breakdown Type", "Priority", "Status", "Artisan", "Breakdown Start",
            "Breakdown End", "Work Start", "Work End", "Delay Start", "Delay End",
            "Response Time (minutes)", "Repair Time (minutes)", "Delay Time (minutes)",
            "Downtime (minutes)", "Response Time (hours)", "Repair Time (hours)",
            "Delay Time (hours)", "Downtime (hours)", "Total Spare Cost",
            "Root Cause", "Immediate Cause", "Work Done", "Recommendations"
        ]
        writer.writerow(headers)
        
        # Write data rows
        for record in records:
            row = [
                record.get('id', ''),
                record.get('date', ''),
                record.get('machine_id', ''),
                record.get('machine_name', ''),
                record.get('location', ''),
                record.get('department', ''),
                record.get('breakdown_type', ''),
                record.get('priority', ''),
                record.get('status', ''),
                record.get('artisan_name', ''),
                record.get('breakdown_start', ''),
                record.get('breakdown_end', ''),
                record.get('work_start', ''),
                record.get('work_end', ''),
                record.get('delay_start', ''),
                record.get('delay_end', ''),
                record.get('response_time_minutes', 0),
                record.get('repair_time_minutes', 0),
                record.get('delay_time_minutes', 0),
                record.get('downtime_minutes', 0),
                record.get('response_time_hours', 0.0),
                record.get('repair_time_hours', 0.0),
                record.get('delay_time_hours', 0.0),
                record.get('downtime_hours', 0.0),
                record.get('total_spare_cost', 0.0),
                record.get('root_cause', ''),
                record.get('immediate_cause', ''),
                record.get('work_done', ''),
                record.get('artisan_recommendations', '')
            ]
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        
        # Create filename with date range
        if start_date and end_date:
            filename = f"breakdowns_{start_date}_{end_date}.csv"
        else:
            filename = "breakdowns_export.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting breakdowns to CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting breakdowns: {str(e)}")

@app.get("/api/breakdowns/stats/advanced")
async def get_advanced_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    department: Optional[str] = None
):
    """Get advanced breakdown statistics with insights"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Build query
        query = supabase.table("breakdowns").select("*")
        
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
        if department and department != "all":
            query = query.eq("department", department)
        
        response = query.execute()
        records = response.data or []
        
        if not records:
            return {
                "message": "No data available for the selected period",
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
        
        # Calculate basic statistics
        total_breakdowns = len(records)
        
        # Time-based statistics
        total_downtime_minutes = sum((r.get('downtime_minutes', 0) or 0) for r in records)
        total_downtime_hours = sum((r.get('downtime_hours', 0.0) or 0.0) for r in records)
        total_repair_time_minutes = sum((r.get('repair_time_minutes', 0) or 0) for r in records)
        total_delay_time_minutes = sum((r.get('delay_time_minutes', 0) or 0) for r in records)
        
        # Cost statistics
        total_spare_cost = sum((r.get('total_spare_cost', 0.0) or 0.0) for r in records)
        avg_spare_cost = total_spare_cost / total_breakdowns if total_breakdowns > 0 else 0
        
        # Machine statistics
        machine_breakdowns = {}
        for record in records:
            machine = f"{record.get('machine_id', 'Unknown')} - {record.get('machine_name', 'Unknown')}"
            machine_breakdowns[machine] = machine_breakdowns.get(machine, 0) + 1
        
        # Artisan statistics
        artisan_breakdowns = {}
        for record in records:
            artisan = record.get('artisan_name', 'Unknown')
            artisan_breakdowns[artisan] = artisan_breakdowns.get(artisan, 0) + 1
        
        # Time analysis
        response_times = [r.get('response_time_minutes', 0) or 0 for r in records if r.get('response_time_minutes')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        repair_times = [r.get('repair_time_minutes', 0) or 0 for r in records if r.get('repair_time_minutes')]
        avg_repair_time = sum(repair_times) / len(repair_times) if repair_times else 0
        
        # Efficiency metrics
        total_productive_time = total_downtime_minutes - total_delay_time_minutes
        efficiency_percentage = (total_productive_time / total_downtime_minutes * 100) if total_downtime_minutes > 0 else 0
        
        # Trends (if we have enough data)
        date_breakdowns = {}
        for record in records:
            date_str = record.get('date', 'Unknown')
            if date_str:
                # Extract just the date part
                date_part = date_str.split('T')[0] if 'T' in date_str else date_str
                date_breakdowns[date_part] = date_breakdowns.get(date_part, 0) + 1
        
        # Top problematic machines (by downtime)
        machine_downtime = {}
        for record in records:
            machine = record.get('machine_id', 'Unknown')
            downtime = record.get('downtime_minutes', 0) or 0
            machine_downtime[machine] = machine_downtime.get(machine, 0) + downtime
        
        top_problematic_machines = dict(sorted(machine_downtime.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Breakdown by time of day (if time data is available)
        time_of_day_breakdowns = {"Morning": 0, "Afternoon": 0, "Evening": 0, "Night": 0}
        for record in records:
            breakdown_time = record.get('breakdown_start')
            if breakdown_time:
                try:
                    hour = int(breakdown_time.split(':')[0])
                    if 6 <= hour < 12:
                        time_of_day_breakdowns["Morning"] += 1
                    elif 12 <= hour < 18:
                        time_of_day_breakdowns["Afternoon"] += 1
                    elif 18 <= hour < 24:
                        time_of_day_breakdowns["Evening"] += 1
                    else:
                        time_of_day_breakdowns["Night"] += 1
                except:
                    pass
        
        return {
            "summary": {
                "total_breakdowns": total_breakdowns,
                "total_downtime_minutes": total_downtime_minutes,
                "total_downtime_hours": round(total_downtime_hours, 2),
                "total_repair_time_minutes": total_repair_time_minutes,
                "total_delay_time_minutes": total_delay_time_minutes,
                "total_spare_cost": round(total_spare_cost, 2),
                "avg_spare_cost_per_breakdown": round(avg_spare_cost, 2),
                "avg_response_time_minutes": round(avg_response_time, 2),
                "avg_repair_time_minutes": round(avg_repair_time, 2),
                "efficiency_percentage": round(efficiency_percentage, 2)
            },
            "breakdowns_by_machine": dict(sorted(machine_breakdowns.items(), key=lambda x: x[1], reverse=True)[:10]),
            "breakdowns_by_artisan": dict(sorted(artisan_breakdowns.items(), key=lambda x: x[1], reverse=True)[:10]),
            "daily_trends": dict(sorted(date_breakdowns.items())[-30:]),  # Last 30 days
            "top_problematic_machines": top_problematic_machines,
            "time_of_day_analysis": time_of_day_breakdowns,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating advanced stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating advanced stats: {str(e)}")

@app.get("/api/breakdowns/dashboard/overview")
async def get_dashboard_overview():
    """Get comprehensive dashboard overview"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Get today's date
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Total breakdowns
        total_response = supabase.table("breakdowns").select("id", count="exact").execute()
        total_breakdowns = total_response.count if hasattr(total_response, 'count') else len(total_response.data or [])
        
        # This week's breakdowns
        week_response = supabase.table("breakdowns").select("id", count="exact").gte("date", week_ago.isoformat()).execute()
        week_breakdowns = week_response.count if hasattr(week_response, 'count') else len(week_response.data or [])
        
        # This month's breakdowns
        month_response = supabase.table("breakdowns").select("id", count="exact").gte("date", month_ago.isoformat()).execute()
        month_breakdowns = month_response.count if hasattr(month_response, 'count') else len(month_response.data or [])
        
        # Open breakdowns
        open_response = supabase.table("breakdowns").select("id", count="exact").in_("status", ["logged", "in_progress"]).execute()
        open_breakdowns = open_response.count if hasattr(open_response, 'count') else len(open_response.data or [])
        
        # High priority breakdowns
        priority_response = supabase.table("breakdowns").select("id", count="exact").eq("priority", "high").execute()
        high_priority = priority_response.count if hasattr(priority_response, 'count') else len(priority_response.data or [])
        
        # Critical priority breakdowns
        critical_response = supabase.table("breakdowns").select("id", count="exact").eq("priority", "critical").execute()
        critical_priority = critical_response.count if hasattr(critical_response, 'count') else len(critical_response.data or [])
        
        # Today's breakdowns
        today_response = supabase.table("breakdowns").select("*").eq("date", today.isoformat()).execute()
        today_breakdowns = today_response.data or []
        today_count = len(today_breakdowns)
        
        # Calculate today's total downtime
        today_downtime = sum((b.get('downtime_minutes', 0) or 0) for b in today_breakdowns)
        today_downtime_hours = round(today_downtime / 60, 2)
        
        # Recent breakdowns (last 10)
        recent_response = supabase.table("breakdowns").select("*").order("created_at", desc=True).limit(10).execute()
        recent_breakdowns = recent_response.data or []
        
        # Breakdown by type (for chart)
        type_response = supabase.table("breakdowns").select("breakdown_type").gte("date", month_ago.isoformat()).execute()
        type_counts = {}
        if type_response.data:
            for record in type_response.data:
                b_type = record.get('breakdown_type', 'Unknown')
                type_counts[b_type] = type_counts.get(b_type, 0) + 1
        
        return {
            "metrics": {
                "total_breakdowns": total_breakdowns,
                "week_breakdowns": week_breakdowns,
                "month_breakdowns": month_breakdowns,
                "open_breakdowns": open_breakdowns,
                "high_priority": high_priority,
                "critical_priority": critical_priority,
                "today_breakdowns": today_count,
                "today_downtime_minutes": today_downtime,
                "today_downtime_hours": today_downtime_hours
            },
            "recent_breakdowns": recent_breakdowns,
            "breakdown_by_type": type_counts,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard overview: {str(e)}")

@app.get("/api/breakdowns/analytics/time-analysis")
async def get_time_analysis(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Get detailed time analysis of breakdowns"""
    try:
        if supabase is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        # Build query
        query = supabase.table("breakdowns").select("*")
        
        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())
        
        response = query.execute()
        records = response.data or []
        
        # Initialize analysis
        analysis = {
            "response_time_analysis": {
                "total_minutes": 0,
                "average_minutes": 0,
                "max_minutes": 0,
                "min_minutes": float('inf'),
                "distribution": {"0-15min": 0, "15-30min": 0, "30-60min": 0, "60+min": 0}
            },
            "repair_time_analysis": {
                "total_minutes": 0,
                "average_minutes": 0,
                "max_minutes": 0,
                "min_minutes": float('inf'),
                "distribution": {"0-30min": 0, "30-60min": 0, "1-2h": 0, "2-4h": 0, "4h+": 0}
            },
            "downtime_analysis": {
                "total_minutes": 0,
                "average_minutes": 0,
                "max_minutes": 0,
                "min_minutes": float('inf'),
                "distribution": {"0-1h": 0, "1-4h": 0, "4-8h": 0, "8-24h": 0, "24h+": 0}
            },
            "delay_analysis": {
                "total_minutes": 0,
                "average_minutes": 0,
                "count_with_delay": 0,
                "common_reasons": {}
            }
        }
        
        # Process each record
        response_times = []
        repair_times = []
        downtimes = []
        
        for record in records:
            # Response time analysis
            resp_time = record.get('response_time_minutes', 0) or 0
            if resp_time > 0:
                response_times.append(resp_time)
                analysis["response_time_analysis"]["total_minutes"] += resp_time
                
                # Update min/max
                if resp_time > analysis["response_time_analysis"]["max_minutes"]:
                    analysis["response_time_analysis"]["max_minutes"] = resp_time
                if resp_time < analysis["response_time_analysis"]["min_minutes"]:
                    analysis["response_time_analysis"]["min_minutes"] = resp_time
                
                # Categorize
                if resp_time <= 15:
                    analysis["response_time_analysis"]["distribution"]["0-15min"] += 1
                elif resp_time <= 30:
                    analysis["response_time_analysis"]["distribution"]["15-30min"] += 1
                elif resp_time <= 60:
                    analysis["response_time_analysis"]["distribution"]["30-60min"] += 1
                else:
                    analysis["response_time_analysis"]["distribution"]["60+min"] += 1
            
            # Repair time analysis
            repair_time = record.get('repair_time_minutes', 0) or 0
            if repair_time > 0:
                repair_times.append(repair_time)
                analysis["repair_time_analysis"]["total_minutes"] += repair_time
                
                # Update min/max
                if repair_time > analysis["repair_time_analysis"]["max_minutes"]:
                    analysis["repair_time_analysis"]["max_minutes"] = repair_time
                if repair_time < analysis["repair_time_analysis"]["min_minutes"]:
                    analysis["repair_time_analysis"]["min_minutes"] = repair_time
                
                # Categorize
                if repair_time <= 30:
                    analysis["repair_time_analysis"]["distribution"]["0-30min"] += 1
                elif repair_time <= 60:
                    analysis["repair_time_analysis"]["distribution"]["30-60min"] += 1
                elif repair_time <= 120:
                    analysis["repair_time_analysis"]["distribution"]["1-2h"] += 1
                elif repair_time <= 240:
                    analysis["repair_time_analysis"]["distribution"]["2-4h"] += 1
                else:
                    analysis["repair_time_analysis"]["distribution"]["4h+"] += 1
            
            # Downtime analysis
            downtime = record.get('downtime_minutes', 0) or 0
            if downtime > 0:
                downtimes.append(downtime)
                analysis["downtime_analysis"]["total_minutes"] += downtime
                
                # Update min/max
                if downtime > analysis["downtime_analysis"]["max_minutes"]:
                    analysis["downtime_analysis"]["max_minutes"] = downtime
                if downtime < analysis["downtime_analysis"]["min_minutes"]:
                    analysis["downtime_analysis"]["min_minutes"] = downtime
                
                # Categorize
                if downtime <= 60:
                    analysis["downtime_analysis"]["distribution"]["0-1h"] += 1
                elif downtime <= 240:
                    analysis["downtime_analysis"]["distribution"]["1-4h"] += 1
                elif downtime <= 480:
                    analysis["downtime_analysis"]["distribution"]["4-8h"] += 1
                elif downtime <= 1440:
                    analysis["downtime_analysis"]["distribution"]["8-24h"] += 1
                else:
                    analysis["downtime_analysis"]["distribution"]["24h+"] += 1
            
            # Delay analysis
            delay_time = record.get('delay_time_minutes', 0) or 0
            if delay_time > 0:
                analysis["delay_analysis"]["total_minutes"] += delay_time
                analysis["delay_analysis"]["count_with_delay"] += 1
                
                # Track delay reasons
                delay_reason = record.get('delay_reason', 'Unknown')
                if delay_reason:
                    analysis["delay_analysis"]["common_reasons"][delay_reason] = \
                        analysis["delay_analysis"]["common_reasons"].get(delay_reason, 0) + 1
        
        # Calculate averages
        if response_times:
            analysis["response_time_analysis"]["average_minutes"] = round(sum(response_times) / len(response_times), 2)
        if analysis["response_time_analysis"]["min_minutes"] == float('inf'):
            analysis["response_time_analysis"]["min_minutes"] = 0
        
        if repair_times:
            analysis["repair_time_analysis"]["average_minutes"] = round(sum(repair_times) / len(repair_times), 2)
        if analysis["repair_time_analysis"]["min_minutes"] == float('inf'):
            analysis["repair_time_analysis"]["min_minutes"] = 0
        
        if downtimes:
            analysis["downtime_analysis"]["average_minutes"] = round(sum(downtimes) / len(downtimes), 2)
        if analysis["downtime_analysis"]["min_minutes"] == float('inf'):
            analysis["downtime_analysis"]["min_minutes"] = 0
        
        if analysis["delay_analysis"]["count_with_delay"] > 0:
            analysis["delay_analysis"]["average_minutes"] = round(
                analysis["delay_analysis"]["total_minutes"] / analysis["delay_analysis"]["count_with_delay"], 2
            )
        
        # Convert to hours for better readability
        analysis["response_time_analysis"]["total_hours"] = round(analysis["response_time_analysis"]["total_minutes"] / 60, 2)
        analysis["repair_time_analysis"]["total_hours"] = round(analysis["repair_time_analysis"]["total_minutes"] / 60, 2)
        analysis["downtime_analysis"]["total_hours"] = round(analysis["downtime_analysis"]["total_minutes"] / 60, 2)
        analysis["delay_analysis"]["total_hours"] = round(analysis["delay_analysis"]["total_minutes"] / 60, 2)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error performing time analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error performing time analysis: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)