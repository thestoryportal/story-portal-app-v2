"""Feedback endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID
from ..models import FeedbackEntry, FeedbackCreate, FeedbackUpdate
from ..services import FeedbackStore
from ..database import db

router = APIRouter(prefix="/feedback", tags=["feedback"])

def get_feedback_store():
    return FeedbackStore(db.get_pool())

@router.post("/", response_model=FeedbackEntry, status_code=201)
async def record_feedback(feedback_data: FeedbackCreate, store: FeedbackStore = Depends(get_feedback_store)):
    return await store.record_feedback(feedback_data)

@router.get("/", response_model=list[FeedbackEntry])
async def list_feedback(agent_id: Optional[UUID] = None, limit: int = 100, store: FeedbackStore = Depends(get_feedback_store)):
    return await store.list_feedback(agent_id, limit)

@router.get("/unprocessed", response_model=list[FeedbackEntry])
async def get_unprocessed_feedback(limit: int = 100, store: FeedbackStore = Depends(get_feedback_store)):
    return await store.get_unprocessed_feedback(limit)

@router.get("/{feedback_id}", response_model=FeedbackEntry)
async def get_feedback(feedback_id: UUID, store: FeedbackStore = Depends(get_feedback_store)):
    feedback = await store.get_feedback(feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback

@router.patch("/{feedback_id}", response_model=FeedbackEntry)
async def update_feedback(feedback_id: UUID, feedback_data: FeedbackUpdate, store: FeedbackStore = Depends(get_feedback_store)):
    feedback = await store.update_feedback(feedback_id, feedback_data)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback
