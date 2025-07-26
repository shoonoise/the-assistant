"""Weather forecast activities."""

import logging
from dataclasses import dataclass

from temporalio import activity

from the_assistant.db import get_user_service
from the_assistant.integrations.telegram.constants import SettingKey
from the_assistant.integrations.weather.weather_client import WeatherClient
from the_assistant.models.weather import WeatherForecast

logger = logging.getLogger(__name__)


@dataclass
class GetWeatherForecastInput:
    user_id: int
    location: str | None = None
    days: int = 1


@activity.defn
async def get_weather_forecast(input: GetWeatherForecastInput) -> list[WeatherForecast]:
    """Retrieve weather forecast for a user."""

    location = input.location
    if location is None:
        user_service = get_user_service()
        location = await user_service.get_setting(input.user_id, SettingKey.LOCATION)
        if location is None:
            logger.warning(
                "No location set for user %s; skipping weather forecast",
                input.user_id,
            )
            return []

    client = WeatherClient()
    return await client.get_forecast(location, days=input.days)
