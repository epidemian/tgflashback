import datetime
import logging

from telegram import BotCommand
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot import db, handlers
from bot.config import TARGET_CHAT_ID, TELEGRAM_TOKEN, TIMEZONE

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
    application.add_handler(CommandHandler("chatid", handlers.cmd_chatid))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text_message)
    )
    application.add_handler(
        ChatMemberHandler(handlers.on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    if TARGET_CHAT_ID is not None:
        # days: 0-6 = sunday-saturday (PTB convention). Saturday = 6.
        application.job_queue.run_daily(
            handlers.announce_new_edition,
            time=datetime.time(9, 0, tzinfo=TIMEZONE),
            days=(6,),
            chat_id=TARGET_CHAT_ID,
            name="announce_new_edition",
        )
    else:
        logging.getLogger(__name__).warning(
            "TARGET_CHAT_ID no está configurado: el aviso semanal no se va a mandar. "
            "Usá /chatid en el grupo y agregalo al .env."
        )

    application.run_polling(allowed_updates=["message", "my_chat_member"])


if __name__ == "__main__":
    main()
