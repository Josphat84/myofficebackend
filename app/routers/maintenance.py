from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime, timedelta
import uuid

router = APIRouter()

# Pydantic Models (UPDATED - all IDs as int)
class WorkOrderCreate(BaseModel):
    machine_id: int
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    assigned_to: Optional[int] = None  # CHANGED to Optional[int]
    scheduled_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    tasks: Optional[List[str]] = None

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[int] = None  # CHANGED to Optional[int]
    scheduled_date: Optional[date] = None
    due_date: Optional[date] = None
    actual_hours: Optional[float] = None

class TaskUpdate(BaseModel):
    completed: bool
    notes: Optional[str] = None

class JobCardCreate(BaseModel):
    work_performed: str
    parts_used: Optional[List[dict]] = None
    labor_hours: float
    technician_notes: Optional[str] = None
    supervisor_notes: Optional[str] = None

class RecurringMaintenanceCreate(BaseModel):
    machine_id: int
    title: str
    description: Optional[str] = None
    frequency_days: int
    frequency_type: str = "days"

# Work Order Routes (UPDATED for integer IDs)
@router.post("/work-orders", tags=["Maintenance"])
async def create_work_order(work_order: WorkOrderCreate):
    try:
        work_order_number = f"WO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # First, verify the machine exists
        machine_check = """
            SELECT id, name FROM equipment WHERE id = $1
        """
        machine = await database.fetch_one(machine_check, work_order.machine_id)
        
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        
        # Verify assigned employee exists if provided
        if work_order.assigned_to:
            employee_check = """
                SELECT id, name FROM employees WHERE id = $1
            """
            employee = await database.fetch_one(employee_check, work_order.assigned_to)
            if not employee:
                raise HTTPException(status_code=404, detail="Assigned employee not found")
        
        # Insert work order
        query = """
            INSERT INTO maintenance_work_orders 
            (work_order_number, machine_id, title, description, priority, assigned_to, 
             scheduled_date, due_date, estimated_hours, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        """
        result = await database.fetch_one(query, 
            work_order_number, work_order.machine_id, work_order.title, 
            work_order.description, work_order.priority, work_order.assigned_to,
            work_order.scheduled_date, work_order.due_date, work_order.estimated_hours,
            1  # Replace with actual user ID from auth (integer)
        )
        
        # Insert tasks if provided
        if work_order.tasks:
            for task_desc in work_order.tasks:
                task_query = """
                    INSERT INTO maintenance_tasks (work_order_id, task_description)
                    VALUES ($1, $2)
                """
                await database.execute(task_query, result["id"], task_desc)
        
        return {
            "message": "Work order created successfully", 
            "data": result,
            "machine_name": machine["name"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating work order: {str(e)}")

@router.get("/work-orders", tags=["Maintenance"])
async def get_work_orders(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    machine_id: Optional[int] = Query(None),
    assigned_to: Optional[int] = Query(None),  # CHANGED to int
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    try:
        base_query = """
            SELECT wo.*, 
                   e.name as machine_name, 
                   e.serial_number,
                   emp.name as assigned_to_name,
                   creator.name as created_by_name
            FROM maintenance_work_orders wo
            LEFT JOIN equipment e ON wo.machine_id = e.id
            LEFT JOIN employees emp ON wo.assigned_to = emp.id
            LEFT JOIN employees creator ON wo.created_by = creator.id
            WHERE 1=1
        """
        count_query = """
            SELECT COUNT(*) 
            FROM maintenance_work_orders wo
            WHERE 1=1
        """
        
        params = []
        param_count = 0
        
        if status:
            param_count += 1
            base_query += f" AND wo.status = ${param_count}"
            count_query += f" AND wo.status = ${param_count}"
            params.append(status)
        
        if priority:
            param_count += 1
            base_query += f" AND wo.priority = ${param_count}"
            count_query += f" AND wo.priority = ${param_count}"
            params.append(priority)
            
        if machine_id:
            param_count += 1
            base_query += f" AND wo.machine_id = ${param_count}"
            count_query += f" AND wo.machine_id = ${param_count}"
            params.append(machine_id)
            
        if assigned_to:
            param_count += 1
            base_query += f" AND wo.assigned_to = ${param_count}"
            count_query += f" AND wo.assigned_to = ${param_count}"
            params.append(assigned_to)
        
        # Add ordering and pagination
        base_query += " ORDER BY wo.created_at DESC"
        offset = (page - 1) * limit
        base_query += f" LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])
        
        # Execute queries
        work_orders = await database.fetch_all(base_query, *params)
        total = await database.fetch_val(count_query, *params[:param_count])
        
        return {
            "data": work_orders,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching work orders: {str(e)}")

@router.get("/work-orders/{work_order_id}", tags=["Maintenance"])
async def get_work_order_details(work_order_id: int):  # CHANGED to int
    try:
        # Get work order with details
        wo_query = """
            SELECT wo.*, 
                   e.name as machine_name, e.serial_number, e.model,
                   emp.name as assigned_to_name, emp.email as assigned_to_email,
                   creator.name as created_by_name
            FROM maintenance_work_orders wo
            LEFT JOIN equipment e ON wo.machine_id = e.id
            LEFT JOIN employees emp ON wo.assigned_to = emp.id
            LEFT JOIN employees creator ON wo.created_by = creator.id
            WHERE wo.id = $1
        """
        work_order = await database.fetch_one(wo_query, work_order_id)
        
        if not work_order:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        # Get tasks
        tasks_query = """
            SELECT t.*, emp.name as completed_by_name
            FROM maintenance_tasks t
            LEFT JOIN employees emp ON t.completed_by = emp.id
            WHERE t.work_order_id = $1
            ORDER BY t.created_at
        """
        tasks = await database.fetch_all(tasks_query, work_order_id)
        
        # Get job cards
        job_cards_query = """
            SELECT jc.*, emp.name as completed_by_name
            FROM maintenance_job_cards jc
            LEFT JOIN employees emp ON jc.completed_by = emp.id
            WHERE jc.work_order_id = $1
            ORDER BY jc.completed_at DESC
        """
        job_cards = await database.fetch_all(job_cards_query, work_order_id)
        
        return {
            "work_order": work_order,
            "tasks": tasks,
            "job_cards": job_cards
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching work order details: {str(e)}")

@router.put("/work-orders/{work_order_id}", tags=["Maintenance"])
async def update_work_order(work_order_id: int, update_data: WorkOrderUpdate):  # CHANGED to int
    try:
        # Verify assigned employee exists if provided
        if update_data.assigned_to:
            employee_check = """
                SELECT id, name FROM employees WHERE id = $1
            """
            employee = await database.fetch_one(employee_check, update_data.assigned_to)
            if not employee:
                raise HTTPException(status_code=404, detail="Assigned employee not found")
        
        # Build dynamic update query
        update_fields = []
        params = []
        param_count = 0
        
        for field, value in update_data.dict(exclude_unset=True).items():
            param_count += 1
            update_fields.append(f"{field} = ${param_count}")
            params.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        param_count += 1
        update_fields.append(f"updated_at = ${param_count}")
        params.append(datetime.now())
        
        param_count += 1
        params.append(work_order_id)
        
        query = f"""
            UPDATE maintenance_work_orders 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING *
        """
        
        result = await database.fetch_one(query, *params)
        return {"message": "Work order updated successfully", "data": result}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating work order: {str(e)}")

@router.post("/work-orders/{work_order_id}/complete", tags=["Maintenance"])
async def complete_work_order(work_order_id: int, job_card: JobCardCreate):  # CHANGED to int
    try:
        async with database.transaction():
            # Update work order status
            update_wo_query = """
                UPDATE maintenance_work_orders 
                SET status = 'completed', completed_date = $1, actual_hours = $2
                WHERE id = $3
                RETURNING *
            """
            await database.execute(update_wo_query, datetime.now(), job_card.labor_hours, work_order_id)
            
            # Create job card
            job_card_query = """
                INSERT INTO maintenance_job_cards 
                (work_order_id, work_performed, parts_used, labor_hours, 
                 technician_notes, supervisor_notes, completed_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
            """
            result = await database.fetch_one(
                job_card_query, work_order_id, job_card.work_performed,
                job_card.parts_used, job_card.labor_hours, job_card.technician_notes,
                job_card.supervisor_notes, 1  # Replace with actual user ID (integer)
            )
            
            return {"message": "Work order completed successfully", "job_card": result}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing work order: {str(e)}")

# Bulk Job Card Generation
@router.post("/work-orders/bulk-complete", tags=["Maintenance"])
async def bulk_complete_work_orders(work_order_ids: List[int]):  # CHANGED to List[int]
    try:
        completed = []
        for wo_id in work_order_ids:
            # Update each work order to completed
            query = """
                UPDATE maintenance_work_orders 
                SET status = 'completed', completed_date = $1
                WHERE id = $2
                RETURNING work_order_number
            """
            result = await database.fetch_one(query, datetime.now(), wo_id)
            completed.append(result["work_order_number"])
        
        return {"message": f"Completed {len(completed)} work orders", "completed": completed}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in bulk completion: {str(e)}")

# Recurring Maintenance Routes
@router.post("/recurring-maintenance", tags=["Maintenance"])
async def create_recurring_maintenance(recurring: RecurringMaintenanceCreate):
    try:
        # Verify machine exists
        machine_check = """
            SELECT id, name FROM equipment WHERE id = $1
        """
        machine = await database.fetch_one(machine_check, recurring.machine_id)
        
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        
        query = """
            INSERT INTO recurring_maintenance 
            (machine_id, title, description, frequency_days, frequency_type)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """
        result = await database.fetch_one(query, 
            recurring.machine_id, recurring.title, recurring.description,
            recurring.frequency_days, recurring.frequency_type
        )
        
        return {
            "message": "Recurring maintenance created", 
            "data": result,
            "machine_name": machine["name"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating recurring maintenance: {str(e)}")

@router.post("/recurring-maintenance/generate-work-orders", tags=["Maintenance"])
async def generate_recurring_work_orders():
    try:
        # Find recurring maintenance that's due
        query = """
            SELECT rm.*, e.name as machine_name
            FROM recurring_maintenance rm
            JOIN equipment e ON rm.machine_id = e.id
            WHERE rm.is_active = true 
            AND (rm.next_due_date IS NULL OR rm.next_due_date <= CURRENT_DATE)
        """
        due_maintenance = await database.fetch_all(query)
        
        generated = []
        for maintenance in due_maintenance:
            # Create work order
            wo_number = f"WO-RECUR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
            
            wo_query = """
                INSERT INTO maintenance_work_orders 
                (work_order_number, machine_id, title, description, priority, scheduled_date)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            """
            work_order = await database.fetch_one(wo_query,
                wo_number, maintenance["machine_id"], maintenance["title"],
                maintenance["description"], "medium", date.today()
            )
            
            # Update next due date
            next_due = date.today() + timedelta(days=maintenance["frequency_days"])
            update_recur_query = """
                UPDATE recurring_maintenance 
                SET last_performed = $1, next_due_date = $2
                WHERE id = $3
            """
            await database.execute(update_recur_query, date.today(), next_due, maintenance["id"])
            
            generated.append(work_order["work_order_number"])
        
        return {"message": f"Generated {len(generated)} work orders", "work_orders": generated}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating work orders: {str(e)}")

# Machine Maintenance History
@router.get("/machines/{machine_id}/maintenance-history", tags=["Maintenance"])
async def get_machine_maintenance_history(machine_id: int):  # CHANGED to int
    try:
        query = """
            SELECT wo.*, jc.work_performed, jc.completed_at,
                   emp.name as completed_by_name
            FROM maintenance_work_orders wo
            LEFT JOIN maintenance_job_cards jc ON wo.id = jc.work_order_id
            LEFT JOIN employees emp ON jc.completed_by = emp.id
            WHERE wo.machine_id = $1 AND wo.status = 'completed'
            ORDER BY jc.completed_at DESC
        """
        history = await database.fetch_all(query, machine_id)
        return {"data": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching maintenance history: {str(e)}")