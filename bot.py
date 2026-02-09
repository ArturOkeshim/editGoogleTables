"""
Шаг 3: вызов логики script.py — новая задача добавляется в таблицу, изменение обновляет строку.
"""
import os
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
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

BTN_NEW = "Новая задача"
BTN_UPDATE = "Изменить существующую задачу"


async def start(update, context):
    context.user_data.pop("mode", None)
    await update.message.reply_text("Выберите действие:", reply_markup=KEYBOARD)


async def on_button(update, context):
    """Пользователь нажал одну из двух кнопок — запоминаем режим и просим написать текст."""
    text = (update.message.text or "").strip()
    if text == BTN_NEW:
        context.user_data["mode"] = "new"
        await update.message.reply_text("Напишите, что нужно сделать (опишите задачу).")
    elif text == BTN_UPDATE:
        context.user_data["mode"] = "update"
        await update.message.reply_text("Напишите, что нужно изменить (например: «задача по отчёту выполнена»).")
    else:
        await on_text(update, context)


async def on_text(update, context):
    """Текстовое сообщение: если выбран режим — вызываем логику script.py и отвечаем результатом."""
    text = (update.message.text or "").strip()
    mode = context.user_data.get("mode")
    editor = context.application.bot_data.get("editor")

    if not editor:
        await update.message.reply_text("Ошибка: таблица не подключена.")
        return

    if mode == "new":
        context.user_data.pop("mode", None)
        try:
            task_dict = Editor.decipher_add_task_command(text, client)
            editor.insert_info(task_dict)
            await update.message.reply_text("Задача добавлена в таблицу.")
        except Exception as e:
            await update.message.reply_text(f"Не удалось добавить задачу: {e}")

    elif mode == "update":
        context.user_data.pop("mode", None)
        try:
            result = editor.search_task_to_update(text, client)
            if not result.get("matched_rows"):
                await update.message.reply_text("Не нашёл подходящую задачу.")
                return
            if not result.get("changes"):
                await update.message.reply_text("Не понял, что нужно изменить.")
                return
            editor.update_info(result)
            row = result["matched_rows"][0]
            await update.message.reply_text(f"Готово. Обновил строку {row-3}.")
        except Exception as e:
            await update.message.reply_text(f"Не удалось обновить: {e}")

    else:
        await update.message.reply_text("Сначала выберите действие кнопкой выше.")


def main():
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
