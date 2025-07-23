from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..settings import get_settings
from .store import UserSettingsStore

router = APIRouter(prefix="/settings", tags=["settings"])


def get_store() -> UserSettingsStore:
    settings = get_settings()
    return UserSettingsStore(settings.database_url)


class SettingValue(BaseModel):
    value: Any


@router.get("/keys")
async def list_keys(store: UserSettingsStore = Depends(get_store)):
    return {"keys": await store.list_keys()}


@router.get("/{user_id}")
async def get_all_settings(user_id: int, store: UserSettingsStore = Depends(get_store)):
    return await store.get_all(user_id)


@router.get("/{user_id}/{key}")
async def get_setting(
    user_id: int, key: str, store: UserSettingsStore = Depends(get_store)
):
    value = await store.get(user_id, key)
    if value is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": key, "value": value}


@router.post("/{user_id}/{key}")
async def set_setting(
    user_id: int,
    key: str,
    setting: SettingValue,
    store: UserSettingsStore = Depends(get_store),
):
    await store.set(user_id, key, setting.value)
    return {"message": "saved"}


@router.delete("/{user_id}/{key}")
async def unset_setting(
    user_id: int, key: str, store: UserSettingsStore = Depends(get_store)
):
    await store.unset(user_id, key)
    return {"message": "deleted"}
