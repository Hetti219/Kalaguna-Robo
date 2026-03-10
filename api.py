"""Async weather API client with caching, timeouts, and rate-limit handling."""

from typing import Optional

import httpx
from cachetools import TTLCache

from config import (
    WEATHER_API_KEY,
    WEATHER_API_BASE,
    API_TIMEOUT,
    CACHE_TTL,
    CACHE_MAX_SIZE,
    logger,
)

# ---------------------------------------------------------------------------
# In-memory TTL cache (keyed by rounded coordinates)
# ---------------------------------------------------------------------------
_weather_cache: TTLCache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)


def _cache_key(lat: float, lon: float) -> str:
    """Generate a cache key from coordinates rounded to 2 decimal places."""
    return f"{round(lat, 2)},{round(lon, 2)}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _fetch_supplemental_data(
    client: httpx.AsyncClient,
    weather_data: dict,
    latitude: float,
    longitude: float,
) -> dict:
    """Fetch air-pollution and OneCall data, merge into *weather_data*."""
    # Air pollution
    pollution_resp = await client.get(
        f"{WEATHER_API_BASE}/air_pollution",
        params={"lat": latitude, "lon": longitude, "appid": WEATHER_API_KEY},
    )
    pollution_data = pollution_resp.json() if pollution_resp.status_code == 200 else {}

    # OneCall API 2.5 (free tier) for UV index & alerts
    onecall_resp = await client.get(
        f"{WEATHER_API_BASE}/onecall",
        params={
            "lat": latitude,
            "lon": longitude,
            "exclude": "minutely,hourly,daily",
            "appid": WEATHER_API_KEY,
            "units": "metric",
        },
    )
    onecall_data = onecall_resp.json() if onecall_resp.status_code == 200 else {}

    # Merge
    weather_data["air_pollution"] = (
        pollution_data["list"][0] if pollution_data.get("list") else None
    )
    weather_data["uvi"] = onecall_data.get("current", {}).get("uvi")
    weather_data["alerts"] = onecall_data.get("alerts", [])

    return weather_data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_weather_by_coordinates(
    latitude: float, longitude: float
) -> Optional[dict]:
    """Return comprehensive weather data for the given coordinates.

    Returns ``None`` on hard errors, or a dict with an ``"error"`` key on
    recoverable issues (e.g. rate limiting).
    """
    cache_key = _cache_key(latitude, longitude)
    if cache_key in _weather_cache:
        return _weather_cache[cache_key]

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            # Current weather
            weather_resp = await client.get(
                f"{WEATHER_API_BASE}/weather",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "appid": WEATHER_API_KEY,
                    "units": "metric",
                },
            )
            weather_resp.raise_for_status()
            weather_data = weather_resp.json()

            # Supplemental data (pollution, UV, alerts)
            weather_data = await _fetch_supplemental_data(
                client, weather_data, latitude, longitude
            )

        _weather_cache[cache_key] = weather_data
        return weather_data

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            logger.warning("OpenWeatherMap rate limit reached.")
            return {"error": "rate_limit"}
        logger.error("HTTP error getting weather data: %s", exc)
        return None
    except httpx.RequestError as exc:
        logger.error("Request error getting weather data: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error in weather data processing: %s", exc)
        return None


async def get_weather_by_city(city_name: str) -> Optional[dict]:
    """Return comprehensive weather data for *city_name*.

    Fetches the ``/weather`` endpoint once to resolve coordinates, then reuses
    those coordinates for supplemental data — avoiding a duplicate call.
    """
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            # Resolve city → coordinates (single /weather call)
            weather_resp = await client.get(
                f"{WEATHER_API_BASE}/weather",
                params={
                    "q": city_name,
                    "appid": WEATHER_API_KEY,
                    "units": "metric",
                },
            )
            weather_resp.raise_for_status()
            weather_data = weather_resp.json()

            latitude = weather_data["coord"]["lat"]
            longitude = weather_data["coord"]["lon"]

            # Check cache before making more requests
            cache_key = _cache_key(latitude, longitude)
            if cache_key in _weather_cache:
                return _weather_cache[cache_key]

            # Supplemental data (pollution, UV, alerts)
            weather_data = await _fetch_supplemental_data(
                client, weather_data, latitude, longitude
            )

        _weather_cache[cache_key] = weather_data
        return weather_data

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            logger.warning("OpenWeatherMap rate limit reached.")
            return {"error": "rate_limit"}
        logger.error("HTTP error getting weather by city: %s", exc)
        return None
    except httpx.RequestError as exc:
        logger.error("Request error getting weather by city: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error getting weather by city: %s", exc)
        return None
