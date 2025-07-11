import importlib

import pytest
from fastapi.testclient import TestClient

from the_assistant.main import app

settings_router = importlib.import_module("the_assistant.user_settings.router")


class FakeUserSettingsStore:
    def __init__(self):
        self.data = {}

    async def get(self, user_id: int, key: str):
        return self.data.get(user_id, {}).get(key)

    async def get_all(self, user_id: int):
        return dict(self.data.get(user_id, {}))

    async def list_keys(self):
        keys = set()
        for user_data in self.data.values():
            keys.update(user_data.keys())
        return sorted(keys)

    async def set(self, user_id: int, key: str, value):
        self.data.setdefault(user_id, {})[key] = value

    async def unset(self, user_id: int, key: str):
        if user_id in self.data:
            self.data[user_id].pop(key, None)
            if not self.data[user_id]:
                self.data.pop(user_id, None)


@pytest.fixture
def client():
    store = FakeUserSettingsStore()
    app.dependency_overrides[settings_router.get_store] = lambda: store
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(settings_router.get_store, None)


def test_set_and_get_setting(client):
    resp = client.post("/settings/1/location", json={"value": "Paris"})
    assert resp.status_code == 200

    resp = client.get("/settings/1/location")
    assert resp.status_code == 200
    assert resp.json() == {"key": "location", "value": "Paris"}


def test_get_missing_setting(client):
    resp = client.get("/settings/1/unknown")
    assert resp.status_code == 404


def test_get_all_settings(client):
    client.post("/settings/2/timezone", json={"value": "UTC"})
    client.post("/settings/2/location", json={"value": "London"})

    resp = client.get("/settings/2")
    assert resp.status_code == 200
    assert resp.json() == {"timezone": "UTC", "location": "London"}


def test_list_keys(client):
    client.post("/settings/3/address", json={"value": "123 St"})
    client.post("/settings/4/location", json={"value": "Berlin"})

    resp = client.get("/settings/keys")
    assert resp.status_code == 200
    assert set(resp.json()["keys"]) == {"address", "location"}


def test_unset_setting(client):
    client.post("/settings/5/about", json={"value": "hi"})

    resp = client.delete("/settings/5/about")
    assert resp.status_code == 200

    resp = client.get("/settings/5/about")
    assert resp.status_code == 404
