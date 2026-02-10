from __future__ import annotations

"""Weather tools backed by WeatherAPI.

Includes:
1) WeatherTool: current weather.
2) ForecastTool: forecast up to 3 days.

The tools:
- declare JSON input schemas so Gemini knows how to call them,
- validate and normalize outputs with Pydantic models,
- expose output schemas for documentation and debugging.
"""

import logging
from typing import Any

import requests
from google.genai import types
from pydantic import BaseModel


class LocationInfo(BaseModel):
    """Shared location payload used by weather tool responses."""

    name: str | None = None
    region: str | None = None
    country: str | None = None
    localtime: str | None = None


class CurrentWeatherResponse(BaseModel):
    """Normalized output schema for current weather."""

    location: LocationInfo
    temperature_c: float | None = None
    temperature_f: float | None = None
    feels_like_c: float | None = None
    feels_like_f: float | None = None
    humidity: int | None = None
    condition: str | None = None
    wind_kph: float | None = None
    wind_mph: float | None = None


class ForecastDay(BaseModel):
    """Normalized output schema for one forecast day."""

    date: str | None = None
    condition: str | None = None
    max_temp_c: float | None = None
    min_temp_c: float | None = None
    max_temp_f: float | None = None
    min_temp_f: float | None = None
    avg_humidity: float | None = None
    chance_of_rain: int | None = None


class ForecastResponse(BaseModel):
    """Normalized output schema for multi-day forecast."""

    location: LocationInfo
    days: list[ForecastDay]


class WeatherTool:
    """Current weather tool.

    Expected model call example:
        {"location": "Tokyo"}
    """

    name = "get_current_weather"

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._logger = logging.getLogger("agent.tools.weather")

    def declaration(self) -> types.FunctionDeclaration:
        # Function schema visible to Gemini.
        return types.FunctionDeclaration(
            name=self.name,
            description="Get the current weather for a city.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. Boston, MA",
                    }
                },
                "required": ["location"],
            },
        )

    def output_schema(self) -> dict[str, Any]:
        """Return JSON schema for the tool output."""
        return CurrentWeatherResponse.model_json_schema()

    def execute(self, location: str) -> dict[str, Any]:
        """Fetch and normalize current weather data."""
        self._logger.info("WeatherTool.execute called: location=%s", location)
        data = self._request("current.json", {"q": location, "aqi": "no"})

        location_data = data.get("location", {})
        current = data.get("current", {})
        condition = current.get("condition", {})

        # Normalize raw response into a predictable shape for the model.
        normalized = {
            "location": {
                "name": location_data.get("name"),
                "region": location_data.get("region"),
                "country": location_data.get("country"),
                "localtime": location_data.get("localtime"),
            },
            "temperature_c": current.get("temp_c"),
            "temperature_f": current.get("temp_f"),
            "feels_like_c": current.get("feelslike_c"),
            "feels_like_f": current.get("feelslike_f"),
            "humidity": current.get("humidity"),
            "condition": condition.get("text"),
            "wind_kph": current.get("wind_kph"),
            "wind_mph": current.get("wind_mph"),
        }

        # Validate and return a clean dict payload.
        response = CurrentWeatherResponse(**normalized)
        self._logger.debug("WeatherTool normalized payload keys=%s", list(normalized.keys()))
        return response.model_dump()

    def _request(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Issue HTTP request to WeatherAPI.

        Security:
        - API key is never written to logs.
        """
        if not self._api_key:
            raise RuntimeError("WEATHERAPI_KEY is not set.")

        url = f"{self._base_url}/{endpoint}"
        full_params = {"key": self._api_key, **params}

        # Never log secrets.
        safe_params = {k: v for k, v in full_params.items() if k != "key"}
        self._logger.info("WeatherAPI request: url=%s params=%s", url, safe_params)

        try:
            response = requests.get(url, params=full_params, timeout=10)
        except requests.RequestException as exc:
            raise RuntimeError(f"Weather API request failed: {exc}") from exc

        self._logger.info("WeatherAPI response: status=%s", response.status_code)

        if response.status_code != 200:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message") or payload.get("message")
            except ValueError:
                message = response.text.strip()
            raise RuntimeError(f"Weather API error ({response.status_code}): {message or 'Unknown error'}")

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError("Weather API returned non-JSON response") from exc


class ForecastTool(WeatherTool):
    """Forecast tool for 1-3 days.

    Expected model call example:
        {"location": "Tokyo", "days": 3}
    """

    name = "get_weather_forecast"

    def declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description="Get a weather forecast for up to 3 days for a city.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. Boston, MA",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days for forecast (1-3).",
                        "minimum": 1,
                        "maximum": 3,
                    },
                },
                "required": ["location"],
            },
        )

    def output_schema(self) -> dict[str, Any]:
        """Return JSON schema for the tool output."""
        return ForecastResponse.model_json_schema()

    def execute(self, location: str, days: int = 3) -> dict[str, Any]:
        """Fetch and normalize forecast data.

        We clamp `days` to 1..3 to keep behavior deterministic,
        even if model provides out-of-range values.
        """
        safe_days = max(1, min(3, int(days)))
        self._logger.info("ForecastTool.execute called: location=%s days=%s", location, safe_days)

        data = self._request(
            "forecast.json",
            {"q": location, "days": safe_days, "aqi": "no", "alerts": "no"},
        )

        location_data = data.get("location", {})
        forecast_days = data.get("forecast", {}).get("forecastday", [])

        normalized_days: list[dict[str, Any]] = []
        for forecast_day in forecast_days:
            day_data = forecast_day.get("day", {})
            condition = day_data.get("condition", {})
            normalized_days.append(
                {
                    "date": forecast_day.get("date"),
                    "condition": condition.get("text"),
                    "max_temp_c": day_data.get("maxtemp_c"),
                    "min_temp_c": day_data.get("mintemp_c"),
                    "max_temp_f": day_data.get("maxtemp_f"),
                    "min_temp_f": day_data.get("mintemp_f"),
                    "avg_humidity": day_data.get("avghumidity"),
                    "chance_of_rain": day_data.get("daily_chance_of_rain"),
                }
            )

        # Normalize forecast into a compact, stable payload.
        normalized = {
            "location": {
                "name": location_data.get("name"),
                "region": location_data.get("region"),
                "country": location_data.get("country"),
                "localtime": location_data.get("localtime"),
            },
            "days": normalized_days,
        }

        response = ForecastResponse(**normalized)
        self._logger.debug("ForecastTool normalized %s day entries", len(normalized_days))
        return response.model_dump()
