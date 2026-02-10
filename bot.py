"""
Шаг 3: вызов логики script.py — новая задача добавляется в таблицу, изменение обновляет строку.
"""
import os
import asyncio
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from script import Editor, client

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PROXY = os.getenv("TELEGRAM_PROXY")
CREDENTIALS_PATH = "calm-photon-486609-u4-96ce79c043ec.json"
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")


KEYBOARD = ReplyKeyboardMarkup(
    [["Новая задача", "Изменить существующую задачу"]],
    resize_keyboard=True,
)

SHEET_CHOICE_KEYBOARD = ReplyKeyboardMarkup(
    [["БСА","ЛАПТЕВ","ПУЗАНОВ","АКВА"]],
    resize_keyboard=True,
)

BTN_NEW = "Новая задача"
BTN_UPDATE = "Изменить существующую задачу"

BTN_BCA= "БСА"
BTN_LAPTEV= "ЛАПТЕВ"
BTN_PUZANOV= "ПУЗАНОВ"
BTN_AQUA= "АКВА"

SHEET_BUTTONS = [BTN_BCA, BTN_LAPTEV, BTN_PUZANOV, BTN_AQUA]

async def start(update, context):
    context.user_data.pop("mode", None)
    context.user_data.pop("sheet", None)
    await update.message.reply_text("Выберите действие:", reply_markup=KEYBOARD)


async def on_button(update, context):
    """
    Пользователь нажал одну из кнопок.
    Шаг 1: выбирает действие (новая задача / изменение).
    Шаг 2: выбирает объект (лист таблицы).
    После этого просим ввести текст команды.
    """
    text = (update.message.text or "").strip()

    # Шаг 1: выбор действия
    if text == BTN_NEW:
        context.user_data["mode"] = "new"
        context.user_data.pop("sheet", None)
        await update.message.reply_text(
            "Выберите объект:",
            reply_markup=SHEET_CHOICE_KEYBOARD,
        )
    elif text == BTN_UPDATE:
        context.user_data["mode"] = "update"
        context.user_data.pop("sheet", None)
        await update.message.reply_text(
            "Выберите объект:",
            reply_markup=SHEET_CHOICE_KEYBOARD,
        )

    # Шаг 2: выбор объекта / листа
    elif text in SHEET_BUTTONS:
        context.user_data["sheet"] = text
        mode = context.user_data.get("mode")
        if mode == "new":
            await update.message.reply_text(
                "Напишите, что нужно сделать (опишите задачу).",
                reply_markup=ReplyKeyboardRemove(),
            )
        elif mode == "update":
            await update.message.reply_text(
                "Напишите, что нужно изменить (например: «задача по отчёту выполнена»).",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            # Объект выбран без выбранного действия — просим начать сначала
            await update.message.reply_text(
                "Сначала выберите действие: 'Новая задача' или 'Изменить существующую задачу'.",
                reply_markup=KEYBOARD,
            )

    # Остальное считаем обычным текстом и передаём в обработчик on_text
    else:
        await on_text(update, context)


async def on_text(update, context):
    """Текстовое сообщение: если выбран режим — вызываем логику script.py и отвечаем результатом."""
    text = (update.message.text or "").strip()
    mode = context.user_data.get("mode")
    sheet_name = context.user_data.get("sheet")
    editor = context.application.bot_data.get("editor")

    if not editor:
        await update.message.reply_text("Ошибка: таблица не подключена.")
        return
    if not sheet_name:
        await update.message.reply_text(
            "Не выбран объект. Сначала выберите действие и объект.",
        )
        return

    if mode == "new":
        # Статус для пользователя: бот обрабатывает команду
        status_msg = await update.message.reply_text("Обрабатываю задачу, подождите...")
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
        context.user_data.pop("mode", None)
        try:
            task_dict = Editor.decipher_add_task_command(text, client)
            editor.insert_info(task_dict, sheet_name=sheet_name)
            await status_msg.edit_text(f"Готово: задача добавлена в таблицу ({sheet_name}).")
        except Exception as e:
            await status_msg.edit_text(f"Не удалось добавить задачу: {e}")

    elif mode == "update":
        status_msg = await update.message.reply_text("Обрабатываю изменения, подождите...")
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
        context.user_data.pop("mode", None)
        try:
            result = editor.search_task_to_update(text, client, sheet_name=sheet_name)
            if not result.get("matched_rows"):
                await status_msg.edit_text("Не нашёл подходящую задачу.")
                return
            if not result.get("changes"):
                await status_msg.edit_text("Не понял, что нужно изменить.")
                return
            editor.update_info(result, sheet_name=sheet_name)
            row = result["matched_rows"][0]
            await status_msg.edit_text(f"Готово. Обновил строку {row-3} на листе {sheet_name}.")
        except Exception as e:
            await status_msg.edit_text(f"Не удалось обновить: {e}")

    else:
        await update.message.reply_text("Сначала выберите действие в панели клавиатуры: 'Новая задача' или 'Изменить существующую задачу'")


def main():
    # Для Python 3.14: явно создаём и назначаем event loop,
    # иначе asyncio.get_event_loop() внутри библиотеки кидает RuntimeError.
    asyncio.set_event_loop(asyncio.new_event_loop())

    editor = Editor(CREDENTIALS_PATH, SPREADSHEET_ID)

    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30,
        proxy=PROXY or None,
    )
    app = (
        Application.builder()
        .token(TOKEN)
        .request(request)
        .build()
    )
    app.bot_data["editor"] = editor

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_button))

    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
