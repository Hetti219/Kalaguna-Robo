"""Telegram bot command and message handlers."""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from config import CHOOSING_OPTION, TYPING_CITY
from api import get_weather_by_coordinates, get_weather_by_city
from formatters import format_weather_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _show_options_keyboard(
    update: Update, _context: ContextTypes.DEFAULT_TYPE, message_text: str
) -> int:
    """Display the options keyboard with a custom message."""
    keyboard = [
        [KeyboardButton("Share my location", request_location=True)],
        [KeyboardButton("Type a city name")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(message_text, reply_markup=reply_markup)
    return CHOOSING_OPTION


async def _send_weather_reply(
    update: Update, weather_data: dict | None, fallback_msg: str
) -> None:
    """Send the formatted weather response or an appropriate error message."""
    if weather_data is None:
        await update.message.reply_text(fallback_msg)
    elif weather_data.get("error") == "rate_limit":
        await update.message.reply_text(
            "⏳ The weather service is temporarily rate-limited. "
            "Please try again in a minute."
        )
    else:
        await update.message.reply_text(format_weather_data(weather_data))


# ---------------------------------------------------------------------------
# Conversation handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user to choose an option."""
    return await _show_options_keyboard(
        update,
        context,
        "Welcome to the Weather Bot! I can provide current weather information.\n\n"
        "Please share your location or choose to type a city name.",
    )


async def restart_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Restart the conversation by showing options again."""
    return await _show_options_keyboard(
        update, context, "What would you like to do next?"
    )


async def option_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle user selection to either share location or type city name."""
    if update.message.text == "Type a city name":
        await update.message.reply_text("Please enter the name of the city:")
        return TYPING_CITY
    return CHOOSING_OPTION


async def handle_location(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle user shared location and provide weather information."""
    loc = update.message.location
    weather_data = await get_weather_by_coordinates(loc.latitude, loc.longitude)
    await _send_weather_reply(
        update,
        weather_data,
        "Sorry, I couldn't retrieve weather information for your location.",
    )
    return await restart_conversation(update, context)


async def handle_city(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle city name input and provide weather information."""
    city_name = update.message.text
    weather_data = await get_weather_by_city(city_name)
    await _send_weather_reply(
        update,
        weather_data,
        f"Sorry, I couldn't find weather information for '{city_name}'.",
    )
    return await restart_conversation(update, context)


# ---------------------------------------------------------------------------
# Shortcut command: /weather <city>
# ---------------------------------------------------------------------------

async def weather_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle ``/weather <city>`` as a quick shortcut."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /weather <city name>\nExample: /weather London"
        )
        return

    city_name = " ".join(context.args)
    weather_data = await get_weather_by_city(city_name)
    await _send_weather_reply(
        update,
        weather_data,
        f"Sorry, I couldn't find weather information for '{city_name}'.",
    )


# ---------------------------------------------------------------------------
# Utility commands
# ---------------------------------------------------------------------------

async def help_command(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "I am a Weather Bot. I can provide you with current weather information.\n\n"
        "Commands:\n"
        "/start - Start interacting with the bot\n"
        "/weather <city> - Quick weather lookup\n"
        "/help - Show this help message\n"
        "/cancel - Cancel the current operation"
    )


async def cancel(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text(
        "Operation cancelled. Send /start to begin again."
    )
    return ConversationHandler.END
