import datetime
import io
import logging

from dateutil import parser as dateutil_parser
from telegram import MessageOriginHiddenUser, MessageOriginUser, Update
from telegram.ext import ContextTypes

from bot import chart, db
from bot.config import ADMIN_TELEGRAM_ID, PLAYER_CODES, TIMEZONE, normalize_code
from bot.parser import parse_flashback_message

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Comandos disponibles:\n"
    "/soy <código> — vinculá tu usuario de Telegram a tu código de jugador "
    "(Se, Mb, Na, Ra, ²H)\n"
    "/tabla [año] — tabla de posiciones (default: año actual)\n"
    "/pendientes [código] — semanas que te faltan jugar, con el link\n"
    "/chatid — id de este chat (para configurar avisos)\n"
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

    replied = message.reply_to_message
    if replied is None:
        await message.reply_text(
            "Tenés que responder (reply) al mensaje de la persona que querés "
            "vincular (puede ser un mensaje reenviado de ella)."
        )
        return

    origin = replied.forward_origin
    if isinstance(origin, MessageOriginUser):
        # Forwarded message: link the original sender, not whoever forwarded it.
        target = origin.sender_user
    elif isinstance(origin, MessageOriginHiddenUser):
        await message.reply_text(
            f"'{origin.sender_user_name}' tiene oculto quién reenvía sus mensajes "
            "en su configuración de privacidad de Telegram, así que no puedo "
            "obtener su usuario desde acá. Pedile que te escriba directamente o "
            "que corra /soy él mismo."
        )
        return
    else:
        target = replied.from_user

    if target is None:
        await message.reply_text(
            "No pude identificar a la persona de ese mensaje."
        )
        return

    db.link_player(code, target.id, target.username)
    await message.reply_text(f"Listo, vinculé a {target.first_name} como {code}.")


async def cmd_puntaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if ADMIN_TELEGRAM_ID is None or user is None or user.id != ADMIN_TELEGRAM_ID:
        await message.reply_text("Este comando es solo para el admin.")
        return

    if len(context.args) != 3:
        await message.reply_text(
            "Uso: /puntaje <código> <fecha DD/MM/YYYY> <puntaje>. "
            "Ejemplo: /puntaje Se 23/08/2026 42"
        )
        return

    code_arg, date_arg, score_arg = context.args

    code = normalize_code(code_arg)
    if code is None:
        await message.reply_text(
            f"Código inválido. Los códigos válidos son: {', '.join(PLAYER_CODES)}"
        )
        return

    try:
        puzzle_date = dateutil_parser.parse(date_arg, dayfirst=True).date().isoformat()
    except (ValueError, OverflowError):
        await message.reply_text("Fecha inválida. Usá el formato DD/MM/YYYY.")
        return

    try:
        score = int(score_arg)
    except ValueError:
        await message.reply_text("El puntaje tiene que ser un número entero.")
        return

    db.upsert_score(player_code=code, puzzle_date=puzzle_date, score=score)

    pretty_date = datetime.date.fromisoformat(puzzle_date).strftime("%d/%m/%Y")
    await message.reply_text(
        f"✅ {code} — {pretty_date}: {score} puntos registrados (por admin)."
    )


def _render_tabla(year: int) -> tuple[str, bytes] | None:
    standings = db.get_standings(year)
    if all(row["played"] == 0 for row in standings):
        return None

    header = f"{'Jugador':<8}{'Suma':>6}{'Prom':>7}{'Jug':>5}{'Vict':>6}"
    lines = [header, "-" * len(header)]
    for row in standings:
        lines.append(
            f"{row['code']:<8}{row['total']:>6}{row['avg']:>7.2f}"
            f"{row['played']:>5}{row['wins']:>6}"
        )

    caption = f"Tabla de posiciones {year}\n<pre>{chr(10).join(lines)}</pre>"

    weekly_scores = db.get_weekly_scores(year)
    png_bytes = chart.render_scores_heatmap(year, weekly_scores)
    return caption, png_bytes


async def cmd_tabla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    year = datetime.date.today().year
    if context.args:
        try:
            year = int(context.args[0])
        except ValueError:
            await message.reply_text("Uso: /tabla [año]")
            return

    rendered = _render_tabla(year)
    if rendered is None:
        await message.reply_text(f"No hay puntajes cargados para {year}.")
        return

    caption, png_bytes = rendered
    await message.reply_photo(
        photo=io.BytesIO(png_bytes),
        caption=caption,
        parse_mode="HTML",
    )


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


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    await update.effective_message.reply_text(f"Chat id: {chat.id}")


async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # No visible message — just server-side logging, so chat ids are
    # recoverable from journalctl without anyone typing /chatid.
    chat = update.effective_chat
    new_member = update.my_chat_member.new_chat_member
    logger.info(
        "Chat member update: chat_id=%s title=%r type=%s status=%s",
        chat.id,
        chat.title,
        chat.type,
        new_member.status,
    )


async def announce_new_edition(context: ContextTypes.DEFAULT_TYPE) -> None:
    # The share message's date is the puzzle's date (e.g. Saturday), but the
    # NYT interactive URL for that same puzzle is dated the day before.
    today = datetime.datetime.now(TIMEZONE).date()
    url = db.interactive_url(today.isoformat())
    pretty = today.strftime("%d/%m")
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"🔮 Salió el Flashback de esta semana ({pretty}). Jugalo acá:\n{url}",
    )

    rendered = _render_tabla(today.year)
    if rendered is not None:
        caption, png_bytes = rendered
        await context.bot.send_photo(
            chat_id=context.job.chat_id,
            photo=io.BytesIO(png_bytes),
            caption=caption,
            parse_mode="HTML",
        )
