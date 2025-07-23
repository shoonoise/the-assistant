"""Weather forecast activities."""

import logging
from dataclasses import dataclass

from temporalio import activity

from the_assistant.integrations.weather.weather_client import WeatherClient
from the_assistant.models.weather import WeatherForecast

logger = logging.getLogger(__name__)


@dataclass
class GetWeatherForecastInput:
    location: str
    days: int = 1


@activity.defn
async def get_weather_forecast(input: GetWeatherForecastInput) -> list[WeatherForecast]:
    """Retrieve weather forecast for a location."""
    client = WeatherClient()
    return await client.get_forecast(input.location, days=input.days)
