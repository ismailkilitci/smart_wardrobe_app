from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass(frozen=True)
class WeatherResult:
    weather: str
    temperature_c: float | None
    precipitation_mm: float | None
    weather_code: int | None
    description: str
    provider: str


RAIN_CODES = {
    51, 53, 55,
    56, 57,
    61, 63, 65,
    66, 67,
    80, 81, 82,
    95, 96, 99,
}
SNOW_CODES = {71, 73, 75, 77, 85, 86}

WEATHER_DESCRIPTIONS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def _as_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _as_int(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def map_open_meteo_weather(
    *,
    temperature_c: float | None,
    precipitation_mm: float | None,
    weather_code: int | None,
) -> str:
    if weather_code in RAIN_CODES or (precipitation_mm is not None and precipitation_mm > 0.2):
        return "rainy"
    if weather_code in SNOW_CODES:
        return "cold"
    if temperature_c is None:
        return "mild"
    if temperature_c >= 26:
        return "hot"
    if temperature_c <= 12:
        return "cold"
    return "mild"


def fetch_current_weather(latitude: float, longitude: float, timeout_seconds: float = 8.0) -> WeatherResult:
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,precipitation,rain,showers,snowfall,weather_code",
            "timezone": "auto",
            "forecast_days": 1,
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{query}"

    with urlopen(url, timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))

    current = payload.get("current") if isinstance(payload, dict) else None
    if not isinstance(current, dict):
        raise RuntimeError("Open-Meteo response does not contain current weather")

    temperature = _as_float(current.get("temperature_2m"))
    weather_code = _as_int(current.get("weather_code"))
    precipitation = _as_float(current.get("precipitation"))

    if precipitation is None:
        rain = _as_float(current.get("rain")) or 0.0
        showers = _as_float(current.get("showers")) or 0.0
        snowfall = _as_float(current.get("snowfall")) or 0.0
        precipitation = rain + showers + snowfall

    mapped = map_open_meteo_weather(
        temperature_c=temperature,
        precipitation_mm=precipitation,
        weather_code=weather_code,
    )

    return WeatherResult(
        weather=mapped,
        temperature_c=temperature,
        precipitation_mm=precipitation,
        weather_code=weather_code,
        description=WEATHER_DESCRIPTIONS.get(weather_code, "unknown"),
        provider="open-meteo",
    )
