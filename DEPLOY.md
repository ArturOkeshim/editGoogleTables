# Развёртывание бота на сервере

## 1. Что менять в проекте для сервера

В коде менять ничего не обязательно. Уже учтено:

- Все секреты и пути берутся из переменных окружения (или `.env`).
- Путь к ключу Google: на сервере можно задать `CREDENTIALS_PATH` в `.env`, иначе используется файл из текущей папки.

На сервере нужно только:

- Скопировать проект (через Git или архив).
- Создать `.env` с теми же переменными, что и локально (см. ниже).
- Положить файл ключа Google (тот же JSON) в нужную папку и указать путь в `CREDENTIALS_PATH`, если он не в корне проекта.

---

## 2. Подготовка сервера

1. Установить Python 3.10+ (или ту версию, на которой запускаешь локально).
2. Клонировать репозиторий (или загрузить файлы):
   ```bash
   git clone <url-репо> bot_for_tasks
   cd bot_for_tasks
   ```
3. Создать виртуальное окружение и зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   pip install -r requirements.txt
   ```
4. Создать `.env` в корне проекта (не коммитить):
   ```
   TELEGRAM_BOT_TOKEN=...
   SPREADSHEET_ID=...
   VSE_GPT_API=...
   CREDENTIALS_PATH=./calm-photon-486609-u4-96ce79c043ec.json
   TELEGRAM_PROXY=   # или оставить пустым, если прокси не нужен
   ```
5. Положить JSON-ключ Google в указанный в `CREDENTIALS_PATH` путь (файл не должен попадать в Git — он уже в `.gitignore`).

---

## 3. Запуск так, чтобы бот не падал при отключении SSH

**Вариант A — systemd (удобно для постоянной работы):**

Создать файл `/etc/systemd/system/telegram-bot.service` (подставь свой путь и пользователя):

```ini
[Unit]
Description=Telegram task bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bot_for_tasks
Environment=PATH=/home/ubuntu/bot_for_tasks/venv/bin
ExecStart=/home/ubuntu/bot_for_tasks/venv/bin/python -m bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Дальше:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

Перезапуск после изменений: `sudo systemctl restart telegram-bot`.

**Вариант B — без systemd (быстрый старт):**

```bash
cd /path/to/bot_for_tasks
source venv/bin/activate
nohup python -m bot > bot.log 2>&1 &
```

Перезапуск: найти процесс (`ps aux | grep bot`), убить, снова запустить ту же команду.

---

## 4. Оперативная корректировка в проде и доработки

- **Код храни в Git.** На сервере — только `git pull`, без правок «руками» в продовом коде.
- **Секреты только в `.env`** на сервере; в репозиторий не коммитить.
- **Обновление прода:** зайти на сервер, `cd bot_for_tasks && git pull`, затем перезапуск:
  - при systemd: `sudo systemctl restart telegram-bot`;
  - при nohup: убить старый процесс и снова запустить `python -m bot`.
- **Тестирование до выката в прод:**
  - Локально: тот же код, свой тестовый бот (отдельный токен в BotFather) и тестовая таблица / лист — в своём `.env`.
  - На сервере (по желанию): отдельная папка или ветка с тестовым ботом и своим `.env`; в прод пуллишь только проверенные изменения.
- **Ветки (по желанию):** `main` = прод, фиксируешь сюда только то, что уже проверил. Доработки вести в отдельной ветке, мержить в `main` после теста — тогда на сервере всегда `git pull origin main` и рестарт.

Итого: в проекте для сервера ничего специально менять не нужно; перенос = копирование кода + настройка `.env` и ключа + запуск через systemd или nohup; корректировки и доработки — через Git и перезапуск бота после `git pull`.
