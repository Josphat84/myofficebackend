"""
Spares Management Router - PostgreSQL/Supabase Version
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
from app.supabase_client import supabase
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()

# Custom JSON encoder to handle date objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

# Pydantic Models matching frontend
class SpareCreate(BaseModel):
    stock_code: str = Field(..., min_length=1, description="Unique stock code")
    description: str = Field(..., min_length=1, description="Part description")
    category: Optional[str] = Field(None, description="Category")
    machine_type: Optional[str] = Field(None, description="Machine type")
    current_quantity: int = Field(0, ge=0, description="Current stock quantity")
    min_quantity: int = Field(1, ge=0, description="Minimum stock level")
    max_quantity: int = Field(5, gt=0, description="Maximum stock level")
    unit_price: float = Field(0.0, ge=0, description="Unit price")
    priority: str = Field("medium", description="Priority level")
    storage_location: Optional[str] = Field(None, description="Storage location")
    supplier: Optional[str] = Field(None, description="Supplier name")
    safety_stock: bool = Field(False, description="Safety stock flag")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

class SpareUpdate(BaseModel):
    stock_code: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = None
    machine_type: Optional[str] = None
    current_quantity: Optional[int] = Field(None, ge=0)
    min_quantity: Optional[int] = Field(None, ge=0)
    max_quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    priority: Optional[str] = None
    storage_location: Optional[str] = None
    supplier: Optional[str] = None
    safety_stock: Optional[bool] = None

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

# Helper function to convert dates in records
def convert_dates_to_iso(record):
    """Convert date objects to ISO format strings for JSON serialization"""
    if isinstance(record, dict):
        for key, value in record.items():
            if isinstance(value, (date, datetime)):
                record[key] = value.isoformat()
    return record

# Helper function to clean data
def clean_data(data: dict) -> dict:
    """Clean data by removing None values and empty strings"""
    cleaned = {}
    for key, value in data.items():
        if value is not None and value != "":
            if isinstance(value, str):
                value = value.strip()
                if value:
                    cleaned[key] = value
            else:
                cleaned[key] = value
    return cleaned

# GET all spares
@router.get("")
async def get_spares(
    search: Optional[str] = Query(None, description="Search in stock code or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get all spares with optional filtering"""
    try:
        query = supabase.table("spares").select("*")
        
        if search:
            query = query.or_(f"stock_code.ilike.%{search}%,description.ilike.%{search}%")
        
        if category:
            query = query.eq("category", category)
        
        if priority:
            query = query.eq("priority", priority)
        
        # Apply ordering and pagination
        query = query.order("stock_code", desc=False).limit(limit).offset(offset)
        
        response = query.execute()
        
        # Convert dates to ISO format for JSON serialization
        records = response.data or []
        for record in records:
            convert_dates_to_iso(record)
            
        return records
        
    except Exception as e:
        logger.error(f"Error fetching spares: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching spares: {str(e)}")

# GET single spare
@router.get("/{spare_id}")
async def get_spare(spare_id: int):
    """Get a specific spare by ID"""
    try:
        response = supabase.table("spares").select("*").eq("id", spare_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Spare part not found")
        
        result = response.data[0]
        convert_dates_to_iso(result)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching spare: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching spare: {str(e)}")

# POST create spare
@router.post("", status_code=201)
async def create_spare(spare: SpareCreate):
    """Create a new spare part"""
    try:
        # Check if stock code already exists
        existing = supabase.table("spares").select("id").eq("stock_code", spare.stock_code).execute()
        
        if existing.data:
            raise HTTPException(status_code=400, detail=f"Stock code '{spare.stock_code}' already exists")
        
        # Insert new spare
        response = supabase.table("spares").insert(spare.dict()).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create spare part")
        
        logger.info(f"Created spare part: {spare.stock_code}")
        
        result = response.data[0]
        convert_dates_to_iso(result)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating spare: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating spare: {str(e)}")

# PUT update spare
@router.put("/{spare_id}")
async def update_spare(spare_id: int, spare_update: SpareUpdate):
    """Update an existing spare part"""
    try:
        # Check if spare exists
        existing = supabase.table("spares").select("*").eq("id", spare_id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Spare part not found")
        
        # Check stock code conflict if updating
        if spare_update.stock_code:
            conflict = supabase.table("spares") \
                .select("id") \
                .eq("stock_code", spare_update.stock_code) \
                .neq("id", spare_id) \
                .execute()
            
            if conflict.data:
                raise HTTPException(status_code=400, detail=f"Stock code '{spare_update.stock_code}' already exists")
        
        # Clean update data
        update_data = clean_data(spare_update.dict(exclude_unset=True))
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")
        
        # Update in database
        response = supabase.table("spares").update(update_data).eq("id", spare_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update spare part")
        
        logger.info(f"Updated spare part: {spare_id}")
        
        result = response.data[0]
        convert_dates_to_iso(result)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating spare: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating spare: {str(e)}")

# DELETE spare
@router.delete("/{spare_id}")
async def delete_spare(spare_id: int):
    """Delete a spare part"""
    try:
        # Check if spare exists
        existing = supabase.table("spares").select("*").eq("id", spare_id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Spare part not found")
        
        spare_data = existing.data[0]
        
        # Delete from database
        supabase.table("spares").delete().eq("id", spare_id).execute()
        
        logger.info(f"Deleted spare part: {spare_id} - {spare_data.get('stock_code', 'Unknown')}")
        
        return {
            "message": "Spare part deleted successfully",
            "id": spare_id,
            "stock_code": spare_data.get('stock_code', 'Unknown')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting spare: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting spare: {str(e)}")

# GET suggestions for a field
@router.get("/suggestions/{field}")
async def get_suggestions(field: str):
    """Get unique values for a field for auto-suggestions"""
    allowed_fields = ['category', 'machine_type', 'priority', 'storage_location', 'supplier']
    
    if field not in allowed_fields:
        raise HTTPException(status_code=400, detail=f"Field '{field}' not allowed for suggestions")
    
    try:
        # Get distinct values
        response = supabase.table("spares").select(field).execute()
        
        if not response.data:
            return {"suggestions": []}
        
        # Extract unique non-empty values
        values = set()
        for item in response.data:
            if field in item and item[field] and str(item[field]).strip():
                values.add(str(item[field]).strip())
        
        suggestions = list(sorted(values))
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Error getting suggestions for {field}: {e}")
        return {"suggestions": []}

# GET statistics
@router.get("/stats/summary")
async def get_stats():
    """Get summary statistics"""
    try:
        # Get all spares
        response = supabase.table("spares").select("*").execute()
        
        if not response.data:
            return {
                "total": 0,
                "out_of_stock": 0,
                "low_stock": 0,
                "critical": 0,
                "safety_stock": 0,
                "total_value": 0
            }
        
        spares = response.data
        total = len(spares)
        
        out_of_stock = 0
        low_stock = 0
        critical = 0
        safety_stock = 0
        total_value = 0
        
        for spare in spares:
            current = spare.get('current_quantity', 0) or 0
            min_qty = spare.get('min_quantity', 1) or 1
            price = spare.get('unit_price', 0) or 0
            
            # Calculate inventory value
            total_value += current * price
            
            # Count statuses
            if current <= 0:
                out_of_stock += 1
            elif current <= min_qty:
                low_stock += 1
            
            # Count critical items
            if spare.get('priority') == 'critical':
                critical += 1
            
            # Count safety stock items
            if spare.get('safety_stock') == True:
                safety_stock += 1
        
        return {
            "total": total,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "critical": critical,
            "safety_stock": safety_stock,
            "total_value": round(total_value, 2)
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return {
            "total": 0,
            "out_of_stock": 0,
            "low_stock": 0,
            "critical": 0,
            "safety_stock": 0,
            "total_value": 0
        }

# Health check endpoint
@router.get("/health/check")
async def spares_health_check():
    """Health check endpoint for spares router"""
    try:
        response = supabase.table("spares").select("id", count="exact").limit(1).execute()
        
        return {
            "status": "healthy", 
            "service": "spares", 
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "table_exists": True
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Test endpoint
@router.get("/test/connection")
async def test_connection():
    """Test database connection"""
    try:
        response = supabase.table("spares").select("id", count="exact").limit(1).execute()
        
        return {
            "status": "ok",
            "database": "connected",
            "table": "spares",
            "record_count": len(response.data) if response.data else 0
        }
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}

# Export data endpoint
@router.get("/export/data")
async def export_spares():
    """Export all spares as JSON"""
    try:
        response = supabase.table("spares").select("*").order("stock_code").execute()
        
        spares = response.data or []
        for record in spares:
            convert_dates_to_iso(record)
        
        return {
            "export_date": datetime.now().isoformat(),
            "count": len(spares),
            "spares": spares
        }
        
    except Exception as e:
        logger.error(f"Error exporting spares: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting spares: {str(e)}")