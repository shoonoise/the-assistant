from datetime import date
from unittest.mock import patch

import pytest

from the_assistant.integrations.weather.weather_client import WeatherClient
from the_assistant.models.weather import WeatherForecast


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass

    def json(self):
        return self._payload


class MockAsyncClient:
    def __init__(self, responses):
        self._responses = responses
        self._index = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        response = self._responses[self._index]
        self._index += 1
        return FakeResponse(response)


@pytest.mark.asyncio
async def test_get_forecast_success():
    geocode = {"results": [{"latitude": 52.52, "longitude": 13.41}]}
    weather = {
        "daily": {
            "time": ["2024-07-10"],
            "weathercode": [1],
            "temperature_2m_max": [25],
            "temperature_2m_min": [15],
        }
    }
    client = WeatherClient()
    with patch("httpx.AsyncClient", return_value=MockAsyncClient([geocode, weather])):
        forecasts = await client.get_forecast("Berlin", days=1)

    assert isinstance(forecasts, list)
    assert len(forecasts) == 1
    forecast = forecasts[0]
    assert isinstance(forecast, WeatherForecast)
    assert forecast.location == "Berlin"
    assert forecast.forecast_date == date(2024, 7, 10)
    assert forecast.temperature_max == 25
    assert forecast.condition == "Mainly clear"


@pytest.mark.asyncio
async def test_get_forecast_location_not_found():
    geocode = {"results": []}
    client = WeatherClient()
    with patch("httpx.AsyncClient", return_value=MockAsyncClient([geocode])):
        with pytest.raises(ValueError):
            await client.get_forecast("Nowhere")


@pytest.mark.asyncio
async def test_get_forecast_multiple_days():
    geocode = {"results": [{"latitude": 52.52, "longitude": 13.41}]}
    weather = {
        "daily": {
            "time": ["2024-07-10", "2024-07-11"],
            "weathercode": [1, 2],
            "temperature_2m_max": [25, 26],
            "temperature_2m_min": [15, 16],
        }
    }
    client = WeatherClient()
    with patch("httpx.AsyncClient", return_value=MockAsyncClient([geocode, weather])):
        forecasts = await client.get_forecast("Berlin", days=2)

    assert isinstance(forecasts, list)
    assert len(forecasts) == 2
    assert forecasts[0].forecast_date == date(2024, 7, 10)
    assert forecasts[1].forecast_date == date(2024, 7, 11)
