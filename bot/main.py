import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot import db, handlers
from bot.config import TELEGRAM_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main() -> None:
    db.init_db()
    db.seed_players()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("soy", handlers.cmd_soy))
    application.add_handler(CommandHandler("vincular", handlers.cmd_vincular))
    application.add_handler(CommandHandler("tabla", handlers.cmd_tabla))
    application.add_handler(CommandHandler("pendientes", handlers.cmd_pendientes))
    application.add_handler(CommandHandler("ayuda", handlers.cmd_ayuda))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text_message)
    )

    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
