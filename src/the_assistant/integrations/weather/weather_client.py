import asyncio
import logging
from datetime import date, datetime

import httpx

from the_assistant.models.weather import HourlyForecast, WeatherForecast

logger = logging.getLogger(__name__)


class WeatherClient:
    """Simple client for the Open-Meteo weather API."""

    GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    HOURLY_VARS = "temperature_2m,weathercode"

    async def _get_coordinates(self, location: str) -> tuple[float, float]:
        """Resolve a location name to latitude and longitude."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.GEO_URL, params={"name": location, "count": 1, "format": "json"}
            )
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results")
        if not results:
            raise ValueError(f"Location '{location}' not found")
        first = results[0]
        return float(first["latitude"]), float(first["longitude"])

    async def get_forecast(self, location: str, days: int = 1) -> list[WeatherForecast]:
        """Get weather forecast for the given location."""
        lat, lon = await self._get_coordinates(location)
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weathercode,temperature_2m_max,temperature_2m_min",
            "forecast_days": days,
            "timezone": "UTC",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.FORECAST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        daily = data.get("daily", {})
        forecasts = []
        for idx in range(len(daily.get("time", []))):
            forecasts.append(
                WeatherForecast(
                    location=location,
                    forecast_date=date.fromisoformat(daily["time"][idx]),
                    weather_code=int(daily["weathercode"][idx]),
                    temperature_max=float(daily["temperature_2m_max"][idx]),
                    temperature_min=float(daily["temperature_2m_min"][idx]),
                )
            )
        return forecasts

    async def get_hourly_forecast(
        self, location: str, day: date
    ) -> list[HourlyForecast]:
        """Get hourly forecast for a specific day."""
        lat, lon = await self._get_coordinates(location)
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": self.HOURLY_VARS,
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "timezone": "UTC",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.FORECAST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        hourly = data.get("hourly", {})
        forecasts = []
        for idx in range(len(hourly.get("time", []))):
            forecasts.append(
                HourlyForecast(
                    timestamp=datetime.fromisoformat(hourly["time"][idx]),
                    weather_code=int(hourly["weathercode"][idx]),
                    temperature=float(hourly["temperature_2m"][idx]),
                )
            )
        return forecasts


if __name__ == "__main__":
    client = WeatherClient()
    forecast = asyncio.run(client.get_forecast("Paris", 1))
    print(forecast)
