"""Entry point for the Kālaguṇa Robō Telegram Weather Bot."""

from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_TOKEN, CHOOSING_OPTION, TYPING_CITY
from handlers import (
    start,
    option_handler,
    handle_location,
    handle_city,
    cancel,
    help_command,
    weather_command,
)


def main() -> None:
    """Build and start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Conversation handler with /help accessible inside a conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_OPTION: [
                MessageHandler(filters.LOCATION, handle_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, option_handler),
            ],
            TYPING_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("help", help_command),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weather", weather_command))

    application.run_polling()


if __name__ == "__main__":
    main()
