"""
Шаг 3: вызов логики script.py — новая задача добавляется в таблицу, изменение обновляет строку.
"""
import os
import asyncio
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.error import TimedOut
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from script import Editor, client, transcribe_voice

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PROXY = os.getenv("TELEGRAM_PROXY")
# Путь к JSON ключу Google; на сервере можно задать через .env (CREDENTIALS_PATH).
CREDENTIALS_PATH = os.getenv("CREDENTIALS_PATH", "calm-photon-486609-u4-96ce79c043ec.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

BTN_NEW = "Новая задача"
BTN_UPDATE = "Изменить существующую задачу"
BTN_BACK = "Назад"
BTN_CANCEL = "Отменить последнее изменение"

BTN_BCA = "БСА"
BTN_LAPTEV = "ЛАПТЕВ"
BTN_PUZANOV = "ПУЗАНОВ"
BTN_AQUA = "АКВА"

KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_NEW, BTN_UPDATE]],
    resize_keyboard=True,
)

SHEET_CHOICE_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_BCA, BTN_LAPTEV, BTN_PUZANOV, BTN_AQUA], [BTN_BACK]],
    resize_keyboard=True,
)

TEXT_STAGE_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_BACK]],
    resize_keyboard=True,
)
KEYBOARD_WITH_CANCEL = ReplyKeyboardMarkup(
    [[BTN_NEW, BTN_UPDATE], [BTN_CANCEL]],
    resize_keyboard=True,
)


SHEET_BUTTONS = [BTN_BCA, BTN_LAPTEV, BTN_PUZANOV, BTN_AQUA]

async def start(update, context):
    context.user_data.pop("mode", None)
    context.user_data.pop("sheet", None)
    main_keyboard = KEYBOARD_WITH_CANCEL if context.user_data.get("last_change") else KEYBOARD
    await update.message.reply_text("Выберите действие:", reply_markup=main_keyboard)


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

    # Кнопка «Назад» — отмена / шаг назад
    elif text == BTN_BACK:
        mode = context.user_data.get("mode")
        sheet = context.user_data.get("sheet")
        has_undo = context.user_data.get("last_change") is not None

        # Если уже выбраны и режим, и объект — возвращаемся к выбору объекта
        if mode and sheet:
            context.user_data.pop("sheet", None)
            await update.message.reply_text(
                "Выберите объект:",
                reply_markup=SHEET_CHOICE_KEYBOARD,
            )
        # Если выбран только режим — возвращаемся к выбору действия
        elif mode and not sheet:
            context.user_data.pop("mode", None)
            main_keyboard = KEYBOARD_WITH_CANCEL if has_undo else KEYBOARD
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=main_keyboard,
            )
        # Если ничего не выбрано — просто показываем основное меню
        else:
            main_keyboard = KEYBOARD_WITH_CANCEL if has_undo else KEYBOARD
            await update.message.reply_text(
                "Вы уже в начале. Выберите действие:",
                reply_markup=main_keyboard,
            )
    elif text == BTN_CANCEL:
        # Отмена последнего изменения (добавление или обновление задачи).
        editor = context.application.bot_data.get("editor")
        last_change = context.user_data.get("last_change")
        if not editor or not last_change:
            await update.message.reply_text(
                "Нет последнего изменения, которое можно отменить.",
                reply_markup=KEYBOARD,
            )
            return

        kind = last_change.get("kind")
        sheet_name = last_change.get("sheet")
        try:
            if kind == "insert":
                row = last_change.get("row")
                if row:
                    editor.delete_row(row_num=row, sheet_name=sheet_name)
            elif kind == "update":
                row = last_change.get("row")
                old_values = last_change.get("old_values") or {}
                if row and old_values:
                    # Используем update_info с "откатными" значениями.
                    revert_result = {
                        "matched_rows": [row],
                        "changes": old_values,
                    }
                    editor.update_info(revert_result, sheet_name=sheet_name)
            else:
                await update.message.reply_text(
                "Не получилось определить, какое изменение отменять.",
                reply_markup=KEYBOARD,
            )
            # Если отмена прошла без исключений — очищаем сохранённое изменение.
            context.user_data.pop("last_change", None)
            await update.message.reply_text(
                "Последнее изменение отменено.",
                reply_markup=KEYBOARD,
            )
        except Exception as e:
            await update.message.reply_text(
                f"Не удалось отменить последнее изменение: {e}",
                reply_markup=KEYBOARD,
            )

    # Шаг 2: выбор объекта / листа
    elif text in SHEET_BUTTONS:
        context.user_data["sheet"] = text
        mode = context.user_data.get("mode")
        if mode == "new":
            await update.message.reply_text(
                "Напишите, что нужно сделать (опишите задачу).",
                reply_markup=TEXT_STAGE_KEYBOARD,
            )
        elif mode == "update":
            await update.message.reply_text(
                "Напишите, что нужно изменить (например: «задача по отчёту выполнена»).",
                reply_markup=TEXT_STAGE_KEYBOARD,
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
    # Текст может прийти либо напрямую из сообщения, либо быть заранее
    # сохранён в user_data (например, после транскрибации голосового сообщения).
    raw_text = context.user_data.pop("pending_text", None)
    if raw_text is None:
        raw_text = update.message.text or ""
    text = raw_text.strip()
    mode = context.user_data.get("mode")
    sheet_name = context.user_data.get("sheet")
    editor = context.application.bot_data.get("editor")

    if not editor:
        await update.message.reply_text(
            "Ошибка: таблица не подключена.",
            reply_markup=KEYBOARD,
        )
        return
    if not sheet_name:
        await update.message.reply_text(
            "Не выбран объект. Сначала выберите действие и объект.",
            reply_markup=KEYBOARD,
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
            row_num = editor.insert_info(task_dict, sheet_name=sheet_name)
            # Сохраняем последнее изменение для возможной отмены.
            context.user_data["last_change"] = {
                "kind": "insert",
                "sheet": sheet_name,
                "row": row_num,
            }
            task_title = (task_dict.get("task") or "").strip()
            await status_msg.edit_text(
                f'Готово: задача "{task_title}" добавлена в таблицу ({sheet_name}).'
            )
        except Exception as e:
            await status_msg.edit_text(f"Не удалось добавить задачу: {e}")
        finally:
            # Сбрасываем выбранный лист и возвращаем основную клавиатуру
            context.user_data.pop("sheet", None)
            await update.message.reply_text(
                "Выберите следующее действие:",
                reply_markup=KEYBOARD_WITH_CANCEL,
            )

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

            # Сохраняем исходные значения для возможности отката.
            matched_rows = result.get("matched_rows") or []
            revert_row = result.get("revert_row") or {}
            changes = result.get("changes") or {}
            if matched_rows and revert_row and changes:
                row_num = matched_rows[0]
                old_values = {
                    k: revert_row.get(k, "")
                    for k in changes.keys()
                }
                context.user_data["last_change"] = {
                    "kind": "update",
                    "sheet": sheet_name,
                    "row": row_num,
                    "old_values": old_values,
                }

            editor.update_info(result, sheet_name=sheet_name)
            chat_reply = (result.get("chat_reply") or "").strip()
            reply_text = chat_reply or f"Готово. Обновил строку {result['matched_rows'][0] - 3} на листе {sheet_name}."
            await status_msg.edit_text(reply_text)
        except Exception as e:
            await status_msg.edit_text(f"Не удалось обновить: {e}")
        finally:
            # Сбрасываем выбранный лист и возвращаем основную клавиатуру
            context.user_data.pop("sheet", None)
            await update.message.reply_text(
                "Выберите следующее действие:",
                reply_markup=KEYBOARD_WITH_CANCEL if context.user_data.get("last_change") else KEYBOARD,
            )

    else:
        await update.message.reply_text(
            "Сначала выберите действие в панели клавиатуры: 'Новая задача' или 'Изменить существующую задачу'",
            reply_markup=KEYBOARD,
        )


async def on_voice(update, context):
    """
    Обработка голосового сообщения.
    Если пользователь находится на шаге ввода команды (после выбора действия и объекта),
    голосовое сообщение транскрибируется и дальше обрабатывается так же, как текст.
    """
    mode = context.user_data.get("mode")
    sheet_name = context.user_data.get("sheet")

    # Голосовое сообщение имеет смысл только на шаге ввода команды
    if not mode or not sheet_name:
        await update.message.reply_text(
            "Сначала выберите действие и объект с помощью кнопок.",
            reply_markup=KEYBOARD,
        )
        return

    voice = update.message.voice
    if not voice:
        await update.message.reply_text("Не удалось прочитать голосовое сообщение.")
        return

    # Скачиваем файл голосового сообщения
    temp_path = f"voice_{update.effective_user.id}_{voice.file_unique_id}.ogg"
    try:
        tg_file = await voice.get_file()
        await tg_file.download_to_drive(temp_path)
    except TimedOut:
        await update.message.reply_text(
            "Не удалось загрузить голосовое сообщение (таймаут). Попробуйте ещё раз или напишите текст.",
            reply_markup=TEXT_STAGE_KEYBOARD,
        )
        return

    try:
        # Транскрибируем аудио в текст через VseGPT / OpenAI
        text = transcribe_voice(temp_path, client)
    except Exception as e:
        await update.message.reply_text(f"Не удалось транскрибировать голосовое сообщение: {e}")
        return
    finally:
        # Пытаемся удалить временный файл (если это нужно)
        try:
            os.remove(temp_path)
        except OSError:
            pass

    # Сохраняем текст в user_data и передаём дальше в стандартную логику
    context.user_data["pending_text"] = text
    await on_text(update, context)


def main():
    # Для Python 3.14: явно создаём и назначаем event loop,
    # иначе asyncio.get_event_loop() внутри библиотеки кидает RuntimeError.
    asyncio.set_event_loop(asyncio.new_event_loop())

    editor = Editor(CREDENTIALS_PATH, SPREADSHEET_ID)

    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=30,   # увеличен для скачивания голосовых файлов
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
    app.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_button))

    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
