"""Document endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from ..models import Document, DocumentCreate, DocumentUpdate
from ..services import DocumentStore
from ..database import db

router = APIRouter(prefix="/documents", tags=["documents"])

def get_document_store():
    return DocumentStore(db.get_pool())

@router.post("/", response_model=Document, status_code=201)
async def create_document(doc_data: DocumentCreate, store: DocumentStore = Depends(get_document_store)):
    return await store.create_document(doc_data)

@router.get("/", response_model=list[Document])
async def list_documents(limit: int = 100, store: DocumentStore = Depends(get_document_store)):
    return await store.list_documents(limit)

@router.get("/{document_id}", response_model=Document)
async def get_document(document_id: UUID, store: DocumentStore = Depends(get_document_store)):
    document = await store.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.patch("/{document_id}", response_model=Document)
async def update_document(document_id: UUID, doc_data: DocumentUpdate, store: DocumentStore = Depends(get_document_store)):
    document = await store.update_document(document_id, doc_data)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: UUID, store: DocumentStore = Depends(get_document_store)):
    deleted = await store.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
