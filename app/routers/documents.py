# document_router.py - FastAPI Router for Document Control System

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Configuration & Router Setup ---
router = APIRouter(
    prefix="/api/documents",
    tags=["Document Control System"],
)

# --- Utility Functions for Data Persistence ---

# Global counters (Simulating database IDs)
next_file_id = 200
next_folder_id = 100

def generate_new_file_id():
    global next_file_id
    next_file_id += 1
    return f'f-{next_file_id}'

def generate_new_folder_id():
    global next_folder_id
    next_folder_id += 1
    return f'd-{next_folder_id}'

def get_current_date_string():
    return datetime.now().strftime('%Y-%m-%d')

def get_file_extension(file_name):
    return file_name.split('.')[-1].lower() if '.' in file_name else ''

# Recursively finds a folder by ID and returns the reference to it
def find_folder_by_id(root, target_id):
    if root['id'] == target_id and root['type'] == 'folder':
        return root
    
    if root.get('children'):
        for child in root['children']:
            found = find_folder_by_id(child, target_id)
            if found:
                return found
    return None

# --- Pydantic Schemas ---

# Define the data structure for the file system items
class FileSystemItem(BaseModel):
    id: str
    name: str
    type: str
    access: str
    size: Optional[str] = None
    date: Optional[str] = None
    version: Optional[str] = None
    url: Optional[str] = None
    versions: Optional[List] = []
    # Recursive field: 'FileSystemItem' needs to be rebuilt after definition
    children: Optional[List['FileSystemItem']] = None 

# Rebuild model to handle recursion
FileSystemItem.model_rebuild()

class CreateFolderRequest(BaseModel):
    name: str
    access: str
    
class UploadFileRequest(BaseModel):
    name: str
    size: int
    access: str

# --- Initial Data (In-Memory Database Simulation) ---
file_system = {
    "id": 'root',
    "name": 'Gold Mine DCS Root',
    "type": 'folder',
    "access": 'Admin',
    "children": [
        {"id": '1', "name": 'Geology & Exploration', "type": 'folder', "access": 'Restricted', "children": [
            {"id": '1-1', "name": 'Drill Hole Logs', "type": 'folder', "access": 'Restricted', "children": [
                {"id": '1-1-1', "name": 'Drill Hole Log Template v1.5.doc', "type": 'doc', "size": '123456', "date": '2025-10-25', "version": '1.5', "url": '/files/drill-log.doc', "access": 'Public', "versions": []},
            ]},
        ]},
        {"id": '2', "name": 'Mining Operations', "type": 'folder', "access": 'Public', "children": [
            {"id": '2-1', "name": 'Standard Operating Procedures', "type": 'folder', "access": 'Public', "children': [
                {"id": '2-1-1', "name": 'Blasting Procedure v8.1.pdf', "type": 'pdf', "size": '2048000', "date": '2025-11-05', "version": '8.1', "url": '/files/blasting-proc.pdf', "access": 'Public', "versions': []},
            ]},
        ]},
        {"id": '3', "name": 'Processing Plant', "type": 'folder', "access": 'Restricted', "children": []},
    ]
}

# --- API Endpoints ---

@router.get("/", response_model=FileSystemItem)
async def get_file_system():
    """Retrieves the entire document file system structure."""
    return file_system

@router.post("/folder/{parent_folder_id}", response_model=FileSystemItem)
async def create_folder(parent_folder_id: str, new_folder_data: CreateFolderRequest):
    """Creates a new subfolder within the specified parent folder."""
    target_folder = find_folder_by_id(file_system, parent_folder_id)
    if not target_folder:
        raise HTTPException(status_code=404, detail="Parent folder not found")

    new_folder = {
        "id": generate_new_folder_id(),
        "name": new_folder_data.name,
        "type": "folder",
        "access": new_folder_data.access,
        "children": [],
    }
    target_folder['children'].insert(0, new_folder)
    
    return new_folder

@router.post("/file/{parent_folder_id}", response_model=FileSystemItem)
async def upload_file(parent_folder_id: str, file_data: UploadFileRequest):
    """Simulates uploading a new file's metadata to the specified folder."""
    target_folder = find_folder_by_id(file_system, parent_folder_id)
    if not target_folder:
        raise HTTPException(status_code=404, detail="Parent folder not found")

    new_file = {
        "id": generate_new_file_id(),
        "name": file_data.name,
        "type": get_file_extension(file_data.name) or 'default',
        "size": str(file_data.size),
        "date": get_current_date_string(),
        "version": '1.0',
        "url": f"/files/{new_file['id']}", 
        "access": file_data.access,
        "versions": [{"version": '1.0', "date": get_current_date_string(), "uploader": 'API Sim'}],
    }
    target_folder['children'].insert(0, new_file)
    
    return new_file

# Example of a deletion route (for future expansion)
@router.delete("/item/{item_id}", status_code=204)
async def delete_item(item_id: str):
    """Placeholder for deleting a file or folder by ID."""
    # (Actual deletion logic would be implemented here)
    # For now, we just simulate a successful deletion.
    if item_id in ['f-201', 'd-101']:
         raise HTTPException(status_code=404, detail="Item not found")
    return