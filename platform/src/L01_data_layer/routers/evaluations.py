"""Evaluation endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID
from ..models import Evaluation, EvaluationCreate
from ..services import EvaluationStore
from ..database import db

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

def get_evaluation_store():
    return EvaluationStore(db.get_pool())

@router.post("/", response_model=Evaluation, status_code=201)
async def record_evaluation(eval_data: EvaluationCreate, store: EvaluationStore = Depends(get_evaluation_store)):
    return await store.record_evaluation(eval_data)

@router.get("/", response_model=list[Evaluation])
async def list_evaluations(agent_id: Optional[UUID] = None, limit: int = 100, store: EvaluationStore = Depends(get_evaluation_store)):
    return await store.list_evaluations(agent_id, limit)

@router.get("/{evaluation_id}", response_model=Evaluation)
async def get_evaluation(evaluation_id: UUID, store: EvaluationStore = Depends(get_evaluation_store)):
    evaluation = await store.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation

@router.get("/agent/{agent_id}/stats")
async def get_agent_stats(agent_id: UUID, store: EvaluationStore = Depends(get_evaluation_store)):
    return await store.get_agent_stats(agent_id)
