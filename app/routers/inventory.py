# backend/app/routers/inventory.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# Pydantic models
class InventoryItem(BaseModel):
    id: str
    name: str
    sku: str
    category: str
    description: str
    currentStock: int
    minStock: int
    maxStock: int
    unit: str
    cost: float
    supplier: str
    location: str
    status: str
    lastRestocked: str
    createdAt: str
    updatedAt: str

class InventoryItemCreate(BaseModel):
    name: str
    sku: str
    category: str
    description: str
    currentStock: int
    minStock: int
    maxStock: int
    unit: str
    cost: float
    supplier: str
    location: str

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    currentStock: Optional[int] = None
    minStock: Optional[int] = None
    maxStock: Optional[int] = None
    unit: Optional[str] = None
    cost: Optional[float] = None
    supplier: Optional[str] = None
    location: Optional[str] = None

# Mock database
inventory_db = {}

def calculate_status(current_stock: int, min_stock: int) -> str:
    if current_stock == 0:
        return "out-of-stock"
    elif current_stock <= min_stock:
        return "low-stock"
    else:
        return "in-stock"

# Initialize with sample data
def init_sample_data():
    sample_items = [
        {
            "id": "inv-001",
            "name": "Industrial Circuit Boards",
            "sku": "CB-IND-005",
            "category": "Electronics",
            "description": "High-temperature circuit boards for manufacturing equipment",
            "currentStock": 45,
            "minStock": 20,
            "maxStock": 100,
            "unit": "pcs",
            "cost": 125.50,
            "supplier": "TechSupply Inc",
            "location": "Shelf A-12",
            "status": "in-stock",
            "lastRestocked": (datetime.now() - timedelta(days=7)).isoformat(),
            "createdAt": (datetime.now() - timedelta(days=30)).isoformat(),
            "updatedAt": (datetime.now() - timedelta(days=7)).isoformat()
        },
        {
            "id": "inv-002",
            "name": "Safety Gloves - Large",
            "sku": "SG-L-100",
            "category": "Safety",
            "description": "Cut-resistant safety gloves, large size",
            "currentStock": 8,
            "minStock": 25,
            "maxStock": 200,
            "unit": "pairs",
            "cost": 12.75,
            "supplier": "SafetyFirst Ltd",
            "location": "Bin C-08",
            "status": "low-stock",
            "lastRestocked": (datetime.now().replace(day=datetime.now().day - 14)).isoformat(),
            "createdAt": (datetime.now().replace(day=datetime.now().day - 45)).isoformat(),
            "updatedAt": (datetime.now().replace(day=datetime.now().day - 14)).isoformat()
        },
        {
            "id": "inv-003",
            "name": "Hydraulic Fluid",
            "sku": "HYD-40W",
            "category": "Consumables",
            "description": "Industrial grade hydraulic fluid, 40W",
            "currentStock": 120,
            "minStock": 50,
            "maxStock": 300,
            "unit": "liters",
            "cost": 8.20,
            "supplier": "Industrial Parts Co",
            "location": "Drum Storage",
            "status": "in-stock",
            "lastRestocked": (datetime.now().replace(day=datetime.now().day - 3)).isoformat(),
            "createdAt": (datetime.now().replace(day=datetime.now().day - 60)).isoformat(),
            "updatedAt": (datetime.now().replace(day=datetime.now().day - 3)).isoformat()
        },
        {
            "id": "inv-004",
            "name": "CNC Cutting Tools",
            "sku": "CNC-CT-3MM",
            "category": "Tools",
            "description": "3mm carbide cutting tools for CNC machines",
            "currentStock": 0,
            "minStock": 15,
            "maxStock": 80,
            "unit": "pcs",
            "cost": 45.00,
            "supplier": "Global Tools",
            "location": "Tool Crib B",
            "status": "out-of-stock",
            "lastRestocked": (datetime.now().replace(day=datetime.now().day - 30)).isoformat(),
            "createdAt": (datetime.now().replace(day=datetime.now().day - 90)).isoformat(),
            "updatedAt": (datetime.now().replace(day=datetime.now().day - 30)).isoformat()
        },
        {
            "id": "inv-005",
            "name": "Laser Printer Toner",
            "sku": "TONER-XL500",
            "category": "Office Supplies",
            "description": "High-yield toner for XL500 series printers",
            "currentStock": 3,
            "minStock": 5,
            "maxStock": 20,
            "unit": "cartridges",
            "cost": 89.99,
            "supplier": "Office Depot",
            "location": "Supply Closet",
            "status": "low-stock",
            "lastRestocked": (datetime.now().replace(day=datetime.now().day - 21)).isoformat(),
            "createdAt": (datetime.now().replace(day=datetime.now().day - 120)).isoformat(),
            "updatedAt": (datetime.now().replace(day=datetime.now().day - 21)).isoformat()
        }
    ]
    
    for item in sample_items:
        inventory_db[item["id"]] = item

# Initialize sample data
init_sample_data()

@router.get("/items", response_model=List[InventoryItem])
async def get_inventory_items(
    category: Optional[str] = None,
    status: Optional[str] = None,
    supplier: Optional[str] = None,
    search: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    items = list(inventory_db.values())
    
    # Apply filters
    if category:
        items = [item for item in items if item["category"] == category]
    if status:
        items = [item for item in items if item["status"] == status]
    if supplier:
        items = [item for item in items if item["supplier"] == supplier]
    if search:
        search_lower = search.lower()
        items = [
            item for item in items 
            if search_lower in item["name"].lower() 
            or search_lower in item["sku"].lower()
            or search_lower in item["description"].lower()
        ]
    
    return items

@router.get("/items/{item_id}", response_model=InventoryItem)
async def get_inventory_item(item_id: str):
    """Get a specific inventory item by ID"""
    if item_id not in inventory_db:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return inventory_db[item_id]

@router.post("/items", response_model=InventoryItem)
async def create_inventory_item(item: InventoryItemCreate):
    """Create a new inventory item"""
    item_id = f"inv-{len(inventory_db) + 1}"
    now = datetime.now().isoformat()
    
    status = calculate_status(item.currentStock, item.minStock)
    
    new_item = InventoryItem(
        id=item_id,
        **item.dict(),
        status=status,
        lastRestocked=now if item.currentStock > 0 else None,
        createdAt=now,
        updatedAt=now
    )
    
    inventory_db[item_id] = new_item.dict()
    return new_item

@router.put("/items/{item_id}", response_model=InventoryItem)
async def update_inventory_item(item_id: str, item_update: InventoryItemUpdate):
    """Update an existing inventory item"""
    if item_id not in inventory_db:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    existing_item = inventory_db[item_id]
    update_data = item_update.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        existing_item[field] = value
    
    # Recalculate status if stock changed
    if 'currentStock' in update_data:
        existing_item['status'] = calculate_status(
            existing_item['currentStock'], 
            existing_item['minStock']
        )
        if update_data['currentStock'] > existing_item['currentStock']:
            existing_item['lastRestocked'] = datetime.now().isoformat()
    
    existing_item['updatedAt'] = datetime.now().isoformat()
    inventory_db[item_id] = existing_item
    
    return existing_item

@router.delete("/items/{item_id}")
async def delete_inventory_item(item_id: str):
    """Delete an inventory item"""
    if item_id not in inventory_db:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    del inventory_db[item_id]
    return {"message": "Inventory item deleted successfully"}

@router.post("/items/{item_id}/restock")
async def restock_item(item_id: str, quantity: int):
    """Restock an inventory item"""
    if item_id not in inventory_db:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    
    item = inventory_db[item_id]
    item['currentStock'] += quantity
    item['status'] = calculate_status(item['currentStock'], item['minStock'])
    item['lastRestocked'] = datetime.now().isoformat()
    item['updatedAt'] = datetime.now().isoformat()
    
    inventory_db[item_id] = item
    return {
        "message": f"Restocked {quantity} units",
        "newStock": item['currentStock'],
        "item": item
    }

@router.get("/stats")
async def get_inventory_stats():
    """Get inventory statistics for dashboard"""
    items = list(inventory_db.values())
    
    total_items = len(items)
    low_stock = len([item for item in items if item['status'] == 'low-stock'])
    out_of_stock = len([item for item in items if item['status'] == 'out-of-stock'])
    total_value = sum(item['currentStock'] * item['cost'] for item in items)
    
    return {
        "totalItems": total_items,
        "lowStock": low_stock,
        "outOfStock": out_of_stock,
        "totalValue": round(total_value, 2)
    }

@router.get("/categories")
async def get_categories():
    """Get all inventory categories"""
    categories = set(item['category'] for item in inventory_db.values())
    return {"categories": sorted(list(categories))}

@router.get("/suppliers")
async def get_suppliers():
    """Get all suppliers"""
    suppliers = set(item['supplier'] for item in inventory_db.values())
    return {"suppliers": sorted(list(suppliers))}