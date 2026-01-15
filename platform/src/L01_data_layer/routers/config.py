"""Configuration endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from ..models import Configuration, ConfigCreate
from ..services import ConfigStore
from ..database import db

router = APIRouter(prefix="/config", tags=["config"])

def get_config_store():
    return ConfigStore(db.get_pool())

@router.get("/{namespace}/{key}", response_model=Configuration)
async def get_config(namespace: str, key: str, store: ConfigStore = Depends(get_config_store)):
    config = await store.get_config(namespace, key)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@router.put("/{namespace}/{key}", response_model=Configuration)
async def set_config(namespace: str, key: str, value: dict, store: ConfigStore = Depends(get_config_store)):
    config_data = ConfigCreate(namespace=namespace, key=key, value=value)
    return await store.set_config(config_data)

@router.get("/{namespace}", response_model=list[Configuration])
async def list_configs(namespace: str, store: ConfigStore = Depends(get_config_store)):
    return await store.list_configs(namespace)
