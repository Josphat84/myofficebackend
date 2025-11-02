# app/routers/operational_viz.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import random

# --- Configuration & Router Setup ---
router = APIRouter(
    prefix="/api/viz",
    tags=["Operational Visualization"],
)

# --- Pydantic Schemas ---
class KPIData(BaseModel):
    """Schema for a single KPI value."""
    name: str
    value: float
    unit: str
    trend: str # e.g., 'up', 'down', 'flat'
    target: float

class ProductionMetric(BaseModel):
    """Schema for production monitoring (e.g., tonnage/hour)."""
    timestamp: str
    area: str
    tonnage: float

class IncidentMetric(BaseModel):
    """Schema for real-time safety incidents."""
    area: str
    incidents_24h: int
    lta_rate: float # Lost Time Accident Rate

class AssetHealth(BaseModel):
    """Schema for asset health monitoring."""
    asset_id: str
    health_score: float # 0 to 100
    status: str # e.g., 'Optimal', 'Warning', 'Critical'
    runtime_hours: int

# --- Mock Data Generation ---

def generate_kpis() -> List[KPIData]:
    """Generates mock data for top-level KPIs."""
    return [
        KPIData(
            name="Tons Mined (24h)",
            value=random.randint(18000, 22000),
            unit="t",
            trend="up",
            target=20000
        ),
        KPIData(
            name="Overall Equipment Effectiveness (OEE)",
            value=round(random.uniform(75, 85), 1),
            unit="%",
            trend="flat",
            target=80.0
        ),
        KPIData(
            name="Lost Time Incident Rate (LTIR)",
            value=round(random.uniform(0.1, 0.4), 2),
            unit="incidents/M hrs",
            trend="down",
            target=0.25
        ),
        KPIData(
            name="Crushing Throughput",
            value=round(random.uniform(750, 850), 0),
            unit="t/h",
            trend="up",
            target=800
        ),
    ]

def generate_production_series() -> List[ProductionMetric]:
    """Generates mock time-series data for a chart."""
    data = []
    base_tonnage = 800
    for i in range(24):
        hour = (datetime.now().hour - i) % 24
        data.append(ProductionMetric(
            timestamp=f"{hour:02d}:00",
            area="Primary Mine",
            tonnage=round(base_tonnage + random.uniform(-100, 100), 2)
        ))
    return list(reversed(data)) # Reverse to show time flowing forward

def generate_asset_health() -> List[AssetHealth]:
    """Generates mock data for critical asset health."""
    assets = ['Crusher-01', 'HaulTruck-15', 'BallMill-02', 'Conveyor-A']
    health_data = []
    
    for asset in assets:
        score = round(random.uniform(40, 100), 0)
        status = 'Optimal'
        if score < 70: status = 'Warning'
        if score < 50: status = 'Critical'
        
        health_data.append(AssetHealth(
            asset_id=asset,
            health_score=score,
            status=status,
            runtime_hours=random.randint(500, 1500)
        ))
    return health_data

# --- API Endpoints ---

@router.get("/kpis", response_model=List[KPIData])
async def get_kpis():
    """Returns top-level key performance indicators for the dashboard."""
    return generate_kpis()

@router.get("/production/timeseries", response_model=List[ProductionMetric])
async def get_production_timeseries():
    """Returns production data over the last 24 hours for charting."""
    return generate_production_series()

@router.get("/assets/health", response_model=List[AssetHealth])
async def get_asset_health():
    """Returns real-time health data for critical assets."""
    return generate_asset_health()

@router.get("/dashboard/summary", response_model=Dict[str, Any])
async def get_dashboard_summary():
    """Combines all data sources for a single dashboard load."""
    return {
        "kpis": generate_kpis(),
        "production_series": generate_production_series(),
        "asset_health": generate_asset_health(),
    }