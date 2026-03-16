import logging
from datetime import datetime, time as dt_time, timedelta
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import Settings, load_settings
from .database import MacroDatabase
from .exercises import EXERCISE_CHOICES, get_exercise_label, parse_exercise_name
from .formatters import (
    dated_title,
    format_confirmation,
    format_exercise_result,
    format_number,
    format_pr_summary,
    format_single_pr,
    format_summary,
)
from .models import ParsedMeal
from .parser import parse_meal

LOGGER = logging.getLogger(__name__)

CALORIES, PROTEIN, FAT, CARBS, NEXT_MEAL, EXERCISE_CHOICE, EXERCISE_WEIGHT = range(7)
MEAL_DATA_KEY = "pending_meal"
EXERCISE_DATA_KEY = "pending_exercise"
NEXT_MEAL_YES = "next_meal_yes"
NEXT_MEAL_NO = "next_meal_no"
EXERCISE_CALLBACK_PREFIX = "exercise:"

HELP_TEXT = (
    "После /start или /add бот задаст 4 вопроса подряд:\n"
    "калории, белки, жиры, углеводы.\n\n"
    "После сохранения бот предложит кнопки для следующего приема пищи.\n\n"
    "Для упражнений используй /exercise, а для просмотра PR используй /pr.\n\n"
    "Можно и старым способом одной строкой:\n"
    "650 ккал, 55 углеводов, 35 белков, 20 жиров\n\n"
    "Команды:\n"
    "/add - добавить прием пищи пошагово\n"
    "/exercise - записать результат упражнения\n"
    "/pr - показать PR по упражнениям\n"
    "/today - итог за текущий день\n"
    "/cancel - отменить текущий ввод\n"
    "/help - подсказка"
)


def _get_database(context: ContextTypes.DEFAULT_TYPE) -> MacroDatabase:
    return context.application.bot_data["db"]


def _get_timezone(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data["timezone"]


def _parse_number(text: str) -> Optional[float]:
    value = text.strip().replace(",", ".")
    try:
        number = float(value)
    except ValueError:
        return None

    if number < 0:
        return None
    return number


def _build_meal_from_user_data(user_data: dict) -> ParsedMeal:
    meal_data = user_data[MEAL_DATA_KEY]
    return ParsedMeal(
        calories=meal_data["calories"],
        carbs=meal_data["carbs"],
        protein=meal_data["protein"],
        fat=meal_data["fat"],
    )


def _build_raw_text(meal: ParsedMeal) -> str:
    return (
        f"{format_number(meal.calories)} ккал, "
        f"{format_number(meal.carbs)} углеводов, "
        f"{format_number(meal.protein)} белков, "
        f"{format_number(meal.fat)} жиров"
    )


def _next_meal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Да", callback_data=NEXT_MEAL_YES),
                InlineKeyboardButton("Нет", callback_data=NEXT_MEAL_NO),
            ]
        ]
    )


def _exercise_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for exercise_key, label in EXERCISE_CHOICES:
        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"{EXERCISE_CALLBACK_PREFIX}{exercise_key}",
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


async def _send_saved_meal_response(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    meal: ParsedMeal,
    meal_logged_at: datetime,
) -> None:
    database = _get_database(context)
    totals = database.get_daily_totals(chat_id, meal_logged_at.date())
    await context.bot.send_message(
        chat_id=chat_id,
        text=format_confirmation(meal, totals),
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text="Добавить еще один прием пищи?",
        reply_markup=_next_meal_keyboard(),
    )


async def _start_meal_dialog(chat_id: Optional[int], context: ContextTypes.DEFAULT_TYPE) -> int:
    if chat_id is None:
        return ConversationHandler.END

    timezone = _get_timezone(context)
    _get_database(context).touch_chat(chat_id, datetime.now(timezone))
    context.user_data.pop(EXERCISE_DATA_KEY, None)
    context.user_data[MEAL_DATA_KEY] = {}
    await context.bot.send_message(
        chat_id=chat_id,
        text="Сейчас запишем прием пищи.\n\n"
        "Сколько калорий в этом приеме пищи?",
    )
    return CALORIES


async def _start_exercise_dialog(chat_id: Optional[int], context: ContextTypes.DEFAULT_TYPE) -> int:
    if chat_id is None:
        return ConversationHandler.END

    timezone = _get_timezone(context)
    _get_database(context).touch_chat(chat_id, datetime.now(timezone))
    context.user_data.pop(MEAL_DATA_KEY, None)
    context.user_data[EXERCISE_DATA_KEY] = {}
    await context.bot.send_message(
        chat_id=chat_id,
        text="Какое упражнение записать?",
        reply_markup=_exercise_keyboard(),
    )
    return EXERCISE_CHOICE


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id if update.effective_chat is not None else None
    return await _start_meal_dialog(chat_id, context)


async def add_meal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id if update.effective_chat is not None else None
    return await _start_meal_dialog(chat_id, context)


async def exercise_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id if update.effective_chat is not None else None
    return await _start_exercise_dialog(chat_id, context)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is not None:
        await update.message.reply_text("Текущий ввод отменен.")
    context.user_data.pop(MEAL_DATA_KEY, None)
    context.user_data.pop(EXERCISE_DATA_KEY, None)
    return ConversationHandler.END


async def calories_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or not update.message.text:
        return CALORIES

    calories = _parse_number(update.message.text)
    if calories is None:
        await update.message.reply_text("Нужно число. Например: 650")
        return CALORIES

    context.user_data[MEAL_DATA_KEY]["calories"] = calories
    await update.message.reply_text("Сколько белков?")
    return PROTEIN


async def protein_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or not update.message.text:
        return PROTEIN

    protein = _parse_number(update.message.text)
    if protein is None:
        await update.message.reply_text("Нужно число. Например: 35")
        return PROTEIN

    context.user_data[MEAL_DATA_KEY]["protein"] = protein
    await update.message.reply_text("Сколько жиров?")
    return FAT


async def fat_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or not update.message.text:
        return FAT

    fat = _parse_number(update.message.text)
    if fat is None:
        await update.message.reply_text("Нужно число. Например: 20")
        return FAT

    context.user_data[MEAL_DATA_KEY]["fat"] = fat
    await update.message.reply_text("Сколько углеводов?")
    return CARBS


async def carbs_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_chat is None or update.message is None or not update.message.text:
        return CARBS

    carbs = _parse_number(update.message.text)
    if carbs is None:
        await update.message.reply_text("Нужно число. Например: 55")
        return CARBS

    context.user_data[MEAL_DATA_KEY]["carbs"] = carbs
    meal = _build_meal_from_user_data(context.user_data)

    timezone = _get_timezone(context)
    now = datetime.now(timezone)
    database = _get_database(context)
    database.add_meal(update.effective_chat.id, now, meal, _build_raw_text(meal))

    context.user_data.pop(MEAL_DATA_KEY, None)
    await _send_saved_meal_response(update.effective_chat.id, context, meal, now)
    return NEXT_MEAL


async def next_meal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query is None:
        return ConversationHandler.END

    query = update.callback_query
    chat_id = update.effective_chat.id if update.effective_chat is not None else None
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    if query.data == NEXT_MEAL_YES:
        return await _start_meal_dialog(chat_id, context)

    if chat_id is not None:
        await context.bot.send_message(chat_id=chat_id, text="Ок. Когда будешь готов, нажми /add.")
    return ConversationHandler.END


async def next_meal_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or not update.message.text:
        return NEXT_MEAL

    normalized = update.message.text.strip().lower()
    if normalized in {"да", "yes", "y"}:
        chat_id = update.effective_chat.id if update.effective_chat is not None else None
        return await _start_meal_dialog(chat_id, context)

    if normalized in {"нет", "no", "n"}:
        await update.message.reply_text("Ок. Когда будешь готов, нажми /add.")
        return ConversationHandler.END

    await update.message.reply_text("Нажми кнопку Да или Нет, либо напиши да или нет.")
    return NEXT_MEAL


async def exercise_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query is None:
        return ConversationHandler.END

    query = update.callback_query
    chat_id = update.effective_chat.id if update.effective_chat is not None else None
    if chat_id is None or query.data is None:
        return ConversationHandler.END

    await query.answer()
    exercise_key = query.data.removeprefix(EXERCISE_CALLBACK_PREFIX)
    context.user_data[EXERCISE_DATA_KEY] = {"exercise_key": exercise_key}
    await query.edit_message_text(text=f"Упражнение: {get_exercise_label(exercise_key)}")
    await context.bot.send_message(chat_id=chat_id, text="Сколько килограммов?")
    return EXERCISE_WEIGHT


async def exercise_choice_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or not update.message.text:
        return EXERCISE_CHOICE

    exercise_key = parse_exercise_name(update.message.text)
    if exercise_key is None:
        labels = ", ".join(label for _, label in EXERCISE_CHOICES)
        await update.message.reply_text(f"Выбери одно из упражнений: {labels}")
        return EXERCISE_CHOICE

    context.user_data[EXERCISE_DATA_KEY] = {"exercise_key": exercise_key}
    await update.message.reply_text(
        f"Упражнение: {get_exercise_label(exercise_key)}\nСколько килограммов?"
    )
    return EXERCISE_WEIGHT


async def exercise_weight_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_chat is None or update.message is None or not update.message.text:
        return EXERCISE_WEIGHT

    weight = _parse_number(update.message.text)
    if weight is None or weight == 0:
        await update.message.reply_text("Нужно число больше 0. Например: 100")
        return EXERCISE_WEIGHT

    exercise_data = context.user_data.get(EXERCISE_DATA_KEY, {})
    exercise_key = exercise_data.get("exercise_key")
    if not exercise_key:
        return await _start_exercise_dialog(update.effective_chat.id, context)

    timezone = _get_timezone(context)
    now = datetime.now(timezone)
    database = _get_database(context)
    previous_record = database.get_personal_record(update.effective_chat.id, exercise_key)
    database.add_exercise_result(update.effective_chat.id, now, exercise_key, weight)
    context.user_data.pop(EXERCISE_DATA_KEY, None)

    await update.message.reply_text(
        format_exercise_result(exercise_key, weight, previous_record)
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None or update.message is None:
        return

    timezone = _get_timezone(context)
    _get_database(context).touch_chat(update.effective_chat.id, datetime.now(timezone))
    await update.message.reply_text(HELP_TEXT)


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None or update.message is None:
        return

    timezone = _get_timezone(context)
    now = datetime.now(timezone)
    database = _get_database(context)
    database.touch_chat(update.effective_chat.id, now)

    totals = database.get_daily_totals(update.effective_chat.id, now.date())
    await update.message.reply_text(format_summary("Итого за сегодня", totals))


async def pr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None or update.message is None:
        return

    timezone = _get_timezone(context)
    now = datetime.now(timezone)
    database = _get_database(context)
    database.touch_chat(update.effective_chat.id, now)

    if context.args:
        exercise_key = parse_exercise_name(" ".join(context.args))
        if exercise_key is None:
            labels = ", ".join(label for _, label in EXERCISE_CHOICES)
            await update.message.reply_text(f"Не понял упражнение. Доступно: {labels}")
            return

        record = database.get_personal_record(update.effective_chat.id, exercise_key)
        await update.message.reply_text(format_single_pr(exercise_key, record))
        return

    records = database.get_personal_records(update.effective_chat.id)
    await update.message.reply_text(format_pr_summary(records))


async def meal_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None or update.message is None or not update.message.text:
        return

    meal = parse_meal(update.message.text)
    if meal is None:
        await update.message.reply_text(
            "Не понял сообщение.\n\n"
            "Попробуй так:\n"
            "650 ккал, 55 углеводов, 35 белков, 20 жиров\n\n"
            "Для упражнений используй /exercise, а для просмотра PR используй /pr."
        )
        return

    timezone = _get_timezone(context)
    now = datetime.now(timezone)
    database = _get_database(context)
    database.add_meal(update.effective_chat.id, now, meal, update.message.text)
    await _send_saved_meal_response(update.effective_chat.id, context, meal, now)


async def send_daily_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    database = _get_database(context)
    timezone = _get_timezone(context)
    report_date = datetime.now(timezone).date() - timedelta(days=1)

    for chat_id in database.list_chat_ids():
        if database.was_report_sent(chat_id, report_date):
            continue

        totals = database.get_daily_totals(chat_id, report_date)
        message = format_summary(dated_title("Итоги за", report_date), totals)

        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception:
            LOGGER.exception("Failed to send daily summary", extra={"chat_id": chat_id})
            continue

        database.mark_report_sent(chat_id, report_date, datetime.now(timezone))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.error is None:
        LOGGER.error("Unhandled bot error without exception details")
        return

    LOGGER.error(
        "Unhandled bot error: %s",
        context.error,
        exc_info=(type(context.error), context.error, context.error.__traceback__),
    )


def build_application(settings: Settings) -> Application:
    database = MacroDatabase(settings.database_path)
    database.init_schema()

    application = Application.builder().token(settings.bot_token).build()
    application.bot_data["db"] = database
    application.bot_data["timezone"] = settings.timezone

    input_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("add", add_meal_command),
            CommandHandler("exercise", exercise_command),
            CallbackQueryHandler(
                next_meal_callback,
                pattern=f"^({NEXT_MEAL_YES}|{NEXT_MEAL_NO})$",
            ),
        ],
        allow_reentry=True,
        states={
            CALORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, calories_input)],
            PROTEIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, protein_input)],
            FAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fat_input)],
            CARBS: [MessageHandler(filters.TEXT & ~filters.COMMAND, carbs_input)],
            NEXT_MEAL: [
                CallbackQueryHandler(
                    next_meal_callback,
                    pattern=f"^({NEXT_MEAL_YES}|{NEXT_MEAL_NO})$",
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, next_meal_text_input),
            ],
            EXERCISE_CHOICE: [
                CallbackQueryHandler(
                    exercise_choice_callback,
                    pattern=f"^{EXERCISE_CALLBACK_PREFIX}.+",
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, exercise_choice_text_input),
            ],
            EXERCISE_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exercise_weight_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    application.add_handler(input_conversation)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("pr", pr_command))
    application.add_handler(CommandHandler(["today", "summary"], today_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, meal_message))
    application.add_error_handler(error_handler)

    if application.job_queue is None:
        raise RuntimeError(
            "JobQueue is unavailable. Install dependencies from requirements.txt."
        )

    application.job_queue.run_daily(
        send_daily_summary,
        time=dt_time(hour=0, minute=0, tzinfo=settings.timezone),
        name="daily-summary",
    )

    return application


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    application = build_application(settings)
    application.run_polling()
