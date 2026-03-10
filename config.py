"""Configuration, constants, and environment validation for the Weather Bot."""

import os
import logging
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
load_dotenv()

TELEGRAM_TOKEN = os.environ.get("BOT_API_TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

if not TELEGRAM_TOKEN or not WEATHER_API_KEY:
    raise RuntimeError(
        "Missing BOT_API_TOKEN or WEATHER_API_KEY – "
        "make sure your .env file exists and contains both keys."
    )

# ---------------------------------------------------------------------------
# Conversation states
# ---------------------------------------------------------------------------
CHOOSING_OPTION, TYPING_CITY = range(2)

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------
WEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
API_TIMEOUT = 10  # seconds

# ---------------------------------------------------------------------------
# Cache settings
# ---------------------------------------------------------------------------
CACHE_TTL = 300  # 5 minutes
CACHE_MAX_SIZE = 100

# ---------------------------------------------------------------------------
# UV-index risk thresholds
# ---------------------------------------------------------------------------
UV_LOW = 3
UV_MODERATE = 6
UV_HIGH = 8
UV_VERY_HIGH = 11

# ---------------------------------------------------------------------------
# Display limits
# ---------------------------------------------------------------------------
MAX_ALERTS = 3
ALERT_DESCRIPTION_MAX_LENGTH = 100
