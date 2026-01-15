"""Event endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID

from ..models import Event, EventCreate
from ..services import EventStore
from ..database import db
from ..redis_client import redis_client

router = APIRouter(prefix="/events", tags=["events"])

def get_event_store():
    return EventStore(db.get_pool(), redis_client)

@router.post("/", response_model=Event, status_code=201)
async def create_event(event_data: EventCreate, store: EventStore = Depends(get_event_store)):
    return await store.create_event(event_data)

@router.get("/", response_model=list[Event])
async def list_events(
    aggregate_id: Optional[UUID] = None,
    aggregate_type: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    store: EventStore = Depends(get_event_store)
):
    return await store.query_events(aggregate_id, aggregate_type, event_type, limit, offset)

@router.get("/{event_id}", response_model=Event)
async def get_event(event_id: UUID, store: EventStore = Depends(get_event_store)):
    event = await store.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
