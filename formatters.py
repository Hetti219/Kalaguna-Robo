"""Format weather data for user-friendly Telegram display."""

from config import (
    UV_LOW,
    UV_MODERATE,
    UV_HIGH,
    UV_VERY_HIGH,
    MAX_ALERTS,
    ALERT_DESCRIPTION_MAX_LENGTH,
    logger,
)


def get_uv_risk_level(uvi: float) -> str:
    """Determine UV risk level based on UV index value."""
    if uvi < UV_LOW:
        return "Low Risk (No protection required)"
    elif uvi < UV_MODERATE:
        return "Moderate Risk (Protection recommended)"
    elif uvi < UV_HIGH:
        return "High Risk (Protection essential)"
    elif uvi < UV_VERY_HIGH:
        return "Very High Risk (Extra protection needed)"
    else:
        return "Extreme Risk (Maximum protection required)"


def get_air_quality_description(aqi: int) -> str:
    """Convert air quality index to descriptive text."""
    descriptions = {
        1: "Excellent (Very Good)",
        2: "Fair (Good)",
        3: "Moderate (Acceptable)",
        4: "Poor (Unhealthy)",
        5: "Very Poor (Hazardous)",
    }
    return descriptions.get(aqi, "Unknown")


def format_weather_data(weather_data: dict) -> str:
    """Format comprehensive weather data into a Telegram-friendly string."""
    if not weather_data:
        return "Error retrieving weather data. Please try again later."

    city_name = weather_data["name"]
    country = weather_data["sys"]["country"]
    weather_description = weather_data["weather"][0]["description"].capitalize()
    temperature = weather_data["main"]["temp"]
    feels_like = weather_data["main"]["feels_like"]
    humidity = weather_data["main"]["humidity"]
    wind_speed = weather_data["wind"]["speed"]

    # Basic weather block
    formatted = (
        f"📍 Location: {city_name}, {country}\n"
        f"🌤 Weather: {weather_description}\n"
        f"🌡 Temperature: {temperature}°C\n"
        f"🤔 Feels like: {feels_like}°C\n"
        f"💧 Humidity: {humidity}%\n"
        f"💨 Wind speed: {wind_speed} m/s"
    )

    # UV Index
    if weather_data.get("uvi") is not None:
        uvi = weather_data["uvi"]
        formatted += f"\n\n☀️ UV Index: {uvi} - {get_uv_risk_level(uvi)}"

    # Air Quality
    if weather_data.get("air_pollution"):
        try:
            aqi = weather_data["air_pollution"]["main"]["aqi"]
            air_quality = get_air_quality_description(aqi)
            formatted += f"\n\n🌬 Air Quality: {air_quality}"

            components = weather_data["air_pollution"].get("components", {})
            if components:
                formatted += (
                    f"\n   - PM2.5: {components.get('pm2_5', 'N/A')} μg/m³"
                    f"\n   - PM10: {components.get('pm10', 'N/A')} μg/m³"
                    f"\n   - NO₂: {components.get('no2', 'N/A')} μg/m³"
                )
        except (KeyError, TypeError) as exc:
            logger.error("Error formatting air quality data: %s", exc)

    # Weather alerts
    alerts = weather_data.get("alerts", [])
    if alerts:
        formatted += "\n\n⚠️ Weather Alerts:"
        for i, alert in enumerate(alerts[:MAX_ALERTS]):
            event = alert.get("event", "Unknown Alert")
            description = alert.get("description", "No details available")
            if len(description) > ALERT_DESCRIPTION_MAX_LENGTH:
                description = description[: ALERT_DESCRIPTION_MAX_LENGTH - 3] + "..."
            formatted += f"\n{i + 1}. {event}: {description}"

    return formatted
