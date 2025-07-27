from datetime import date, datetime

from pydantic import Field, computed_field

from .base import BaseAssistantModel

WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


class HourlyForecast(BaseAssistantModel):
    """Hourly forecast entry."""

    timestamp: datetime = Field(description="Forecast time in UTC")
    weather_code: int = Field(description="Open-Meteo weather code")
    temperature: float = Field(description="Temperature (°C)")

    @computed_field
    @property
    def condition(self) -> str:
        """Human readable weather condition."""
        return WEATHER_CODE_MAP.get(self.weather_code, "Unknown")


class WeatherForecast(BaseAssistantModel):
    """Simple weather forecast returned by the Open-Meteo API."""

    location: str = Field(description="Location name")
    forecast_date: date = Field(description="Forecast date")
    weather_code: int = Field(description="Open-Meteo weather code")
    temperature_max: float = Field(description="Maximum temperature (°C)")
    temperature_min: float = Field(description="Minimum temperature (°C)")
    hourly: list[HourlyForecast] | None = Field(
        default=None,
        description="Hourly forecast entries for this date (UTC)",
    )

    @computed_field
    @property
    def condition(self) -> str:
        """Human readable weather condition."""
        return WEATHER_CODE_MAP.get(self.weather_code, "Unknown")
