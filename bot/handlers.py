import datetime

from telegram import Update
from telegram.ext import ContextTypes

from bot import db
from bot.config import ADMIN_TELEGRAM_ID, PLAYER_CODES, normalize_code
from bot.parser import parse_flashback_message

HELP_TEXT = (
    "Comandos disponibles:\n"
    "/soy <código> — vinculá tu usuario de Telegram a tu código de jugador "
    "(Se, Mb, Na, Ra, ²H)\n"
    "/tabla [año] — tabla de posiciones (default: año actual)\n"
    "/pendientes [código] — semanas que te faltan jugar, con el link\n"
    "/ayuda — este mensaje\n\n"
    "Para cargar un puntaje, simplemente pegá el mensaje que comparte el "
    "juego de Flashback en el grupo."
)


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return

    result = parse_flashback_message(message.text)
    if result is None:
        return

    user = update.effective_user
    player = db.get_player_by_telegram_id(user.id) if user else None
    if player is None:
        await message.reply_text(
            "No te tengo vinculado a ningún jugador todavía. "
            "Usá /soy <código> (Se, Mb, Na, Ra, ²H) para vincularte, "
            "o pedile a un admin que lo haga con /vincular."
        )
        return

    db.upsert_score(
        player_code=player["code"],
        puzzle_date=result.puzzle_date,
        score=result.score,
        chat_id=update.effective_chat.id if update.effective_chat else None,
        message_id=message.message_id,
        raw_text=message.text,
    )

    pretty_date = datetime.date.fromisoformat(result.puzzle_date).strftime("%d/%m/%Y")
    await message.reply_text(
        f"✅ {player['code']} — {pretty_date}: {result.score} puntos registrados."
    )


async def cmd_soy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not context.args:
        await message.reply_text(
            "Uso: /soy <código> (Se, Mb, Na, Ra, ²H). Ejemplo: /soy Se"
        )
        return

    code = normalize_code(context.args[0])
    if code is None:
        await message.reply_text(
            f"Código inválido. Los códigos válidos son: {', '.join(PLAYER_CODES)}"
        )
        return

    player = db.get_player_by_code(code)
    if player["telegram_user_id"] is not None and player["telegram_user_id"] != user.id:
        await message.reply_text(
            f"El código {code} ya está vinculado a otro usuario. "
            "Pedile a un admin que lo corrija con /vincular."
        )
        return

    db.link_player(code, user.id, user.username)
    await message.reply_text(f"Listo, quedaste vinculado como {code}.")


async def cmd_vincular(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if ADMIN_TELEGRAM_ID is None or user is None or user.id != ADMIN_TELEGRAM_ID:
        await message.reply_text("Este comando es solo para el admin.")
        return

    if not context.args:
        await message.reply_text(
            "Uso: /vincular <código> respondiendo (reply) al mensaje de la "
            "persona a vincular."
        )
        return

    code = normalize_code(context.args[0])
    if code is None:
        await message.reply_text(
            f"Código inválido. Los códigos válidos son: {', '.join(PLAYER_CODES)}"
        )
        return

    target = message.reply_to_message.from_user if message.reply_to_message else None
    if target is None:
        await message.reply_text(
            "Tenés que responder (reply) al mensaje de la persona que querés vincular."
        )
        return

    db.link_player(code, target.id, target.username)
    await message.reply_text(f"Listo, vinculé a {target.first_name} como {code}.")


async def cmd_tabla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    year = datetime.date.today().year
    if context.args:
        try:
            year = int(context.args[0])
        except ValueError:
            await message.reply_text("Uso: /tabla [año]")
            return

    standings = db.get_standings(year)
    if all(row["played"] == 0 for row in standings):
        await message.reply_text(f"No hay puntajes cargados para {year}.")
        return

    header = f"{'Jugador':<8}{'Suma':>6}{'Prom':>7}{'Jug':>5}{'Vict':>6}"
    lines = [header, "-" * len(header)]
    for row in standings:
        lines.append(
            f"{row['code']:<8}{row['total']:>6}{row['avg']:>7.2f}"
            f"{row['played']:>5}{row['wins']:>6}"
        )

    text = f"Tabla de posiciones {year}\n<pre>{chr(10).join(lines)}</pre>"
    await message.reply_html(text)


async def cmd_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if context.args:
        code = normalize_code(context.args[0])
        if code is None:
            await message.reply_text(
                f"Código inválido. Los códigos válidos son: {', '.join(PLAYER_CODES)}"
            )
            return
    else:
        player = db.get_player_by_telegram_id(user.id) if user else None
        if player is None:
            await message.reply_text(
                "No sé quién sos. Usá /pendientes <código> o vinculate primero con /soy."
            )
            return
        code = player["code"]

    pending = db.get_pending(code)
    if not pending:
        await message.reply_text(f"{code} no tiene semanas pendientes. 🎉")
        return

    lines = [f"Semanas pendientes para {code}:"]
    for puzzle_date in pending:
        pretty = datetime.date.fromisoformat(puzzle_date).strftime("%d/%m/%Y")
        lines.append(f"- {pretty}: {db.interactive_url(puzzle_date)}")

    await message.reply_text("\n".join(lines), disable_web_page_preview=True)


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(HELP_TEXT)
