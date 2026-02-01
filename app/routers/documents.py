# backend/app/routers/documents.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import json
from app.supabase_client import supabase
from app.auth import get_current_user
from app.utils import generate_slug, format_file_size

router = APIRouter(prefix="/documents", tags=["documents"])

# --- Pydantic Models ---
class DocumentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., description="'folder' or file type")
    parent_id: Optional[UUID] = None
    access_level: str = Field("restricted", pattern="^(public|restricted|admin)$")
    tags: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}

class DocumentCreate(DocumentBase):
    @validator('type')
    def validate_type(cls, v):
        if v not in ['folder', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'png', 'zip']:
            raise ValueError('Invalid document type')
        return v

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[UUID] = None
    access_level: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentResponse(DocumentBase):
    id: UUID
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    version: str
    status: str
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    children_count: Optional[int] = 0

class FolderTree(BaseModel):
    id: UUID
    name: str
    type: str
    children: List['FolderTree'] = []

# --- Helper Functions ---
def get_folder_tree(folder_id: Optional[UUID] = None) -> List[FolderTree]:
    """Recursively build folder tree"""
    query = supabase.table("documents").select("*").eq("type", "folder")
    
    if folder_id:
        query = query.eq("parent_id", folder_id)
    else:
        query = query.is_("parent_id", None)
    
    result = query.order("name").execute()
    folders = result.data
    
    tree = []
    for folder in folders:
        children = get_folder_tree(folder['id'])
        tree.append(FolderTree(
            id=folder['id'],
            name=folder['name'],
            type='folder',
            children=children
        ))
    
    return tree

def check_access(document_id: UUID, user_id: UUID) -> bool:
    """Check if user has access to document"""
    doc_result = supabase.table("documents").select("access_level").eq("id", document_id).execute()
    
    if not doc_result.data:
        return False
    
    document = doc_result.data[0]
    
    # Public access
    if document['access_level'] == 'public':
        return True
    
    # Check permissions
    perm_result = supabase.table("document_permissions").select("*").eq("document_id", document_id).eq("user_id", user_id).execute()
    
    return bool(perm_result.data)

# --- API Routes ---

@router.get("/tree", response_model=List[FolderTree])
async def get_document_tree():
    """Get complete folder tree"""
    try:
        return get_folder_tree()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document tree: {str(e)}")

@router.get("/folder/{folder_id}", response_model=List[DocumentResponse])
async def get_folder_contents(
    folder_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get contents of a specific folder"""
    try:
        # Check access
        if not check_access(folder_id, current_user['id']):
            raise HTTPException(status_code=403, detail="Access denied")
        
        result = supabase.table("documents").select("*, children_count").eq("parent_id", folder_id).order("type").order("name").execute()
        
        if not result.data:
            return []
        
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching folder contents: {str(e)}")

@router.post("/folder", response_model=DocumentResponse)
async def create_folder(
    folder: DocumentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new folder"""
    try:
        if folder.type != 'folder':
            raise HTTPException(status_code=400, detail="Document type must be 'folder'")
        
        # Check parent access if parent_id exists
        if folder.parent_id and not check_access(folder.parent_id, current_user['id']):
            raise HTTPException(status_code=403, detail="Access denied to parent folder")
        
        folder_data = folder.dict()
        folder_data['created_by'] = current_user['id']
        folder_data['id'] = str(uuid4())
        
        result = supabase.table("documents").insert(folder_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create folder")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating folder: {str(e)}")

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    name: str = Query(...),
    parent_id: Optional[UUID] = None,
    access_level: str = Query("restricted"),
    tags: str = Query(""),
    current_user: dict = Depends(get_current_user)
):
    """Upload a new document"""
    try:
        # Check parent access if parent_id exists
        if parent_id and not check_access(parent_id, current_user['id']):
            raise HTTPException(status_code=403, detail="Access denied to parent folder")
        
        # Get file extension and type
        file_extension = file.filename.split('.')[-1].lower()
        file_type = file_extension if file_extension in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'png', 'zip'] else 'file'
        
        # In production: Upload to storage (S3, Supabase Storage, etc.)
        # For now, store metadata only
        file_content = await file.read()
        file_size = len(file_content)
        
        document_data = {
            'id': str(uuid4()),
            'name': name,
            'type': file_type,
            'parent_id': str(parent_id) if parent_id else None,
            'access_level': access_level,
            'tags': tags.split(',') if tags else [],
            'file_size': file_size,
            'mime_type': file.content_type,
            'version': '1.0',
            'created_by': current_user['id'],
            'metadata': {
                'original_filename': file.filename,
                'uploaded_by': current_user['email']
            }
        }
        
        # Insert document
        result = supabase.table("documents").insert(document_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to upload document")
        
        # Create version record
        version_data = {
            'id': str(uuid4()),
            'document_id': document_data['id'],
            'version_number': '1.0',
            'file_size': file_size,
            'mime_type': file.content_type,
            'change_notes': 'Initial upload',
            'created_by': current_user['id']
        }
        
        supabase.table("document_versions").insert(version_data).execute()
        
        # Log activity
        activity_data = {
            'id': str(uuid4()),
            'document_id': document_data['id'],
            'user_id': current_user['id'],
            'action': 'upload',
            'details': {
                'filename': file.filename,
                'size': format_file_size(file_size)
            }
        }
        
        supabase.table("document_activities").insert(activity_data).execute()
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get document details"""
    try:
        if not check_access(document_id, current_user['id']):
            raise HTTPException(status_code=403, detail="Access denied")
        
        result = supabase.table("documents").select("*").eq("id", document_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document: {str(e)}")

@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    update: DocumentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update document metadata"""
    try:
        if not check_access(document_id, current_user['id']):
            raise HTTPException(status_code=403, detail="Access denied")
        
        update_data = update.dict(exclude_unset=True)
        
        result = supabase.table("documents").update(update_data).eq("id", document_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Log activity
        activity_data = {
            'id': str(uuid4()),
            'document_id': str(document_id),
            'user_id': current_user['id'],
            'action': 'update',
            'details': update_data
        }
        
        supabase.table("document_activities").insert(activity_data).execute()
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating document: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Soft delete a document"""
    try:
        if not check_access(document_id, current_user['id']):
            raise HTTPException(status_code=403, detail="Access denied")
        
        result = supabase.table("documents").update({
            'deleted_at': datetime.utcnow().isoformat(),
            'status': 'deleted'
        }).eq("id", document_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Log activity
        activity_data = {
            'id': str(uuid4()),
            'document_id': str(document_id),
            'user_id': current_user['id'],
            'action': 'delete'
        }
        
        supabase.table("document_activities").insert(activity_data).execute()
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@router.get("/search")
async def search_documents(
    query: str = Query(""),
    type: Optional[str] = None,
    tags: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Search documents"""
    try:
        search_query = supabase.table("documents").select("*").ilike("name", f"%{query}%")
        
        if type:
            search_query = search_query.eq("type", type)
        
        if tags:
            tag_list = tags.split(',')
            search_query = search_query.contains("tags", tag_list)
        
        result = search_query.order("updated_at", desc=True).execute()
        
        # Filter by access
        accessible_docs = []
        for doc in result.data or []:
            if check_access(doc['id'], current_user['id']):
                accessible_docs.append(doc)
        
        return accessible_docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")