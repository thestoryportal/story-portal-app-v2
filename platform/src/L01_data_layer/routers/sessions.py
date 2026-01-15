"""Session endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID
from ..models import Session, SessionCreate, SessionUpdate
from ..services import SessionService
from ..database import db
from ..redis_client import redis_client

router = APIRouter(prefix="/sessions", tags=["sessions"])

def get_session_service():
    return SessionService(db.get_pool(), redis_client)

@router.post("/", response_model=Session, status_code=201)
async def create_session(session_data: SessionCreate, service: SessionService = Depends(get_session_service)):
    return await service.create_session(session_data)

@router.get("/", response_model=list[Session])
async def list_sessions(agent_id: Optional[UUID] = None, limit: int = 100, service: SessionService = Depends(get_session_service)):
    return await service.list_sessions(agent_id, limit)

@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: UUID, service: SessionService = Depends(get_session_service)):
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.patch("/{session_id}", response_model=Session)
async def update_session(session_id: UUID, session_data: SessionUpdate, service: SessionService = Depends(get_session_service)):
    session = await service.update_session(session_id, session_data)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
