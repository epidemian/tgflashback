import logging

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot import db, handlers
from bot.config import TELEGRAM_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# httpx logs the full request URL at INFO level, which includes the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

# Only the commands regular players use; /vincular is admin-only and left out
# of the suggestion menu on purpose.
COMMANDS = [
    BotCommand("soy", "Vincular tu usuario a un código de jugador"),
    BotCommand("tabla", "Ver la tabla de posiciones"),
    BotCommand("pendientes", "Ver tus semanas pendientes"),
    BotCommand("ayuda", "Ver la ayuda"),
]


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(COMMANDS)


def main() -> None:
    db.init_db()
    db.seed_players()

    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

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
