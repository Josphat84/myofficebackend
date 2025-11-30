from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import supabase
import os

router = APIRouter(prefix="/api/engineering-reports", tags=["Engineering Reports"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

class EngineeringReport(BaseModel):
    report_date: str
    engineer_name: str
    supervisor: Optional[str] = None
    shift: Optional[str] = None
    overview: Optional[str] = None
    maintenance_completed: Optional[str] = None
    breakdowns: Optional[str] = None
    spares_used: Optional[str] = None
    safety_notes: Optional[str] = None
    availability: Optional[float] = None
    equipment_availability: Optional[Dict[str, Any]] = None


@router.get("/")
def get_reports():
    data = client.table("engineering_reports").select("*").order("report_date", desc=True).execute()
    return data.data


@router.get("/{report_id}")
def get_single(report_id: str):
    data = client.table("engineering_reports").select("*").eq("id", report_id).single().execute()
    return data.data


@router.post("/")
def create_report(report: EngineeringReport):
    result = client.table("engineering_reports").insert(report.dict()).execute()
    if len(result.data) == 0:
        raise HTTPException(500, "Insert failed.")
    return result.data[0]


@router.patch("/{report_id}")
def update_report(report_id: str, report: EngineeringReport):
    result = client.table("engineering_reports").update(report.dict(exclude_unset=True)).eq("id", report_id).execute()
    return result.data


@router.delete("/{report_id}")
def delete_report(report_id: str):
    result = client.table("engineering_reports").delete().eq("id", report_id).execute()
    return {"success": True, "deleted": result.data}
