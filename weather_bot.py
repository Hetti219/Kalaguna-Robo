"""
Telegram Weather Bot
This bot provides weather information based on user location or city queries.
"""
import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# States for conversation handler
CHOOSING_OPTION, TYPING_CITY = range(2)

# Replace with your API keys
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user to choose an option."""
    return await show_options_keyboard(update, context, "Welcome to the Weather Bot! I can provide current weather information.\n\n"
                                       "Please share your location or choose to type a city name.")


async def show_options_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> int:
    """Display the options keyboard with a custom message."""
    keyboard = [
        [KeyboardButton("Share my location", request_location=True)],
        [KeyboardButton("Type a city name")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(message_text, reply_markup=reply_markup)

    return CHOOSING_OPTION


async def restart_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Restart the conversation by showing options again."""
    return await show_options_keyboard(update, context, "What would you like to do next?")


async def option_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user selection to either share location or type city name."""
    if update.message.text == "Type a city name":
        await update.message.reply_text("Please enter the name of the city:")
        return TYPING_CITY
    return CHOOSING_OPTION


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user shared location and provide weather information."""
    user_location = update.message.location
    weather_data = get_weather_by_coordinates(
        user_location.latitude, user_location.longitude)

    if weather_data:
        await update.message.reply_text(format_weather_data(weather_data))
    else:
        await update.message.reply_text("Sorry, I couldn't retrieve weather information for your location.")

    # Return to start state instead of ending conversation
    return await restart_conversation(update, context)


async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle city name input and provide weather information."""
    city_name = update.message.text
    weather_data = get_weather_by_city(city_name)

    if weather_data:
        await update.message.reply_text(format_weather_data(weather_data))
    else:
        await update.message.reply_text(f"Sorry, I couldn't find weather information for '{city_name}'.")

    # Return to start state instead of ending conversation
    return await restart_conversation(update, context)


def get_weather_by_coordinates(latitude: float, longitude: float) -> dict:
    """Get comprehensive weather data from OpenWeatherMap API using coordinates."""
    try:
        # Get current weather data
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={WEATHER_API_KEY}&units=metric"
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        # Get air pollution data
        pollution_url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={WEATHER_API_KEY}"
        pollution_response = requests.get(pollution_url)
        pollution_response.raise_for_status()
        pollution_data = pollution_response.json()

        # Get UV index and alerts from One Call API
        onecall_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={latitude}&lon={longitude}&exclude=minutely,hourly,daily&appid={WEATHER_API_KEY}&units=metric"
        onecall_response = requests.get(onecall_url)
        onecall_response.raise_for_status()
        onecall_data = onecall_response.json()

        # Combine all data
        combined_data = weather_data
        combined_data["air_pollution"] = pollution_data["list"][0] if pollution_data.get(
            "list") else None
        combined_data["uvi"] = onecall_data.get("current", {}).get("uvi")
        combined_data["alerts"] = onecall_data.get("alerts", [])

        return combined_data
    except Exception as e:
        logger.error(
            f"Error getting comprehensive weather data by coordinates: {e}")
        return None


def get_weather_by_city(city_name: str) -> dict:
    """Get comprehensive weather data from OpenWeatherMap API using city name."""
    try:
        # First get basic weather data to extract coordinates
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={WEATHER_API_KEY}&units=metric"
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        # Extract coordinates
        latitude = weather_data["coord"]["lat"]
        longitude = weather_data["coord"]["lon"]

        # Use coordinates to get comprehensive weather data
        return get_weather_by_coordinates(latitude, longitude)
    except Exception as e:
        logger.error(f"Error getting comprehensive weather data by city: {e}")
        return None


def format_weather_data(weather_data: dict) -> str:
    """Format comprehensive weather data for precise, user-friendly display."""
    city_name = weather_data["name"]
    country = weather_data["sys"]["country"]
    weather_description = weather_data["weather"][0]["description"].capitalize(
    )
    temperature = weather_data["main"]["temp"]
    feels_like = weather_data["main"]["feels_like"]
    humidity = weather_data["main"]["humidity"]
    wind_speed = weather_data["wind"]["speed"]

    # Format basic weather information
    formatted_data = (
        f"📍 Location: {city_name}, {country}\n"
        f"🌤 Weather: {weather_description}\n"
        f"🌡 Temperature: {temperature}°C\n"
        f"🤔 Feels like: {feels_like}°C\n"
        f"💧 Humidity: {humidity}%\n"
        f"💨 Wind speed: {wind_speed} m/s"
    )

    # Add UV Index information if available
    if weather_data.get("uvi") is not None:
        uvi = weather_data["uvi"]
        uv_risk = get_uv_risk_level(uvi)
        formatted_data += f"\n\n☀️ UV Index: {uvi} - {uv_risk}"

    # Add Air Quality information if available
    if weather_data.get("air_pollution"):
        aqi = weather_data["air_pollution"]["main"]["aqi"]
        air_quality = get_air_quality_description(aqi)
        formatted_data += f"\n\n🌬 Air Quality: {air_quality}"

        # Add pollutant details
        components = weather_data["air_pollution"]["components"]
        formatted_data += (
            f"\n   - PM2.5: {components.get('pm2_5', 'N/A')} μg/m³"
            f"\n   - PM10: {components.get('pm10', 'N/A')} μg/m³"
            f"\n   - NO₂: {components.get('no2', 'N/A')} μg/m³"
        )

    # Add weather alerts if available
    if weather_data.get("alerts") and len(weather_data["alerts"]) > 0:
        formatted_data += "\n\n⚠️ Weather Alerts:"
        # Limit to 3 alerts
        for i, alert in enumerate(weather_data["alerts"][:3]):
            event = alert.get("event", "Unknown Alert")
            description = alert.get("description", "No details available")
            # Truncate description if too long
            if len(description) > 100:
                description = description[:97] + "..."
            formatted_data += f"\n{i+1}. {event}: {description}"

    return formatted_data


def get_uv_risk_level(uvi: float) -> str:
    """Determine UV risk level based on UV index value."""
    if uvi < 3:
        return "Low Risk (No protection required)"
    elif uvi < 6:
        return "Moderate Risk (Protection recommended)"
    elif uvi < 8:
        return "High Risk (Protection essential)"
    elif uvi < 11:
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
        5: "Very Poor (Hazardous)"
    }
    return descriptions.get(aqi, "Unknown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "I am a Weather Bot. I can provide you with current weather information.\n\n"
        "Commands:\n"
        "/start - Start interacting with the bot\n"
        "/help - Show this help message\n"
        "/cancel - Cancel the current operation"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text("Operation cancelled. Send /start to begin again.")
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_OPTION: [
                MessageHandler(filters.LOCATION, handle_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               option_handler),
            ],
            TYPING_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    main()
