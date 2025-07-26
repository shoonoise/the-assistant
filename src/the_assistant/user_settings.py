from __future__ import annotations

from typing import Any

from pydantic import RootModel

from .integrations.telegram.constants import SettingKey
from .models.base import BaseAssistantModel


class BaseSetting:
    """Mixin providing conversion helper."""

    def to_python(self) -> Any:
        return self.root  # type: ignore[attr-defined]


class StringSetting(BaseSetting, RootModel[str]):
    """Simple string setting."""

    def to_python(self) -> Any:  # pragma: no cover - trivial
        return self.root


class StringListSetting(BaseSetting, RootModel[list[str]]):
    """List of strings setting."""

    def to_python(self) -> Any:  # pragma: no cover - trivial
        return self.root


class MemoryItem(BaseAssistantModel):
    """Single user memory entry."""

    user_input: str


class MemoriesSetting(BaseSetting, RootModel[dict[str, MemoryItem]]):
    """Collection of user memories keyed by timestamp."""

    def to_python(self) -> Any:
        return {k: v.model_dump() for k, v in self.root.items()}


SETTING_SCHEMAS: dict[SettingKey, type] = {
    SettingKey.GREET: StringSetting,
    SettingKey.BRIEFING_TIME: StringSetting,
    SettingKey.ABOUT_ME: StringSetting,
    SettingKey.LOCATION: StringSetting,
    SettingKey.IGNORE_EMAILS: StringListSetting,
    SettingKey.MEMORIES: MemoriesSetting,
}
