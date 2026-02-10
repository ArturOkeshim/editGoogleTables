"""
Скрипт для тестирования транскрибации речи вне бота.
Использует VseGPT (stt-openai/whisper-1).

Запуск:
    python transcribe.py <путь_к_аудиофайлу>
    python transcribe.py speech.mp3
    python transcribe.py voice_123.ogg
"""
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("VSE_GPT_API")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.vsegpt.ru/v1",
)


def transcribe_voice(file_path: str, client: OpenAI) -> str:
    """
    Транскрибирует аудиофайл в текст через VseGPT (Whisper).
    """
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="stt-openai/whisper-1",
            response_format="json",
            language="ru",
            file=audio_file,
        )

    if hasattr(response, "text"):
        return response.text
    if isinstance(response, dict) and "text" in response:
        return str(response["text"])
    return str(response)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python transcribe.py <путь_к_аудиофайлу>")
        print("Пример: python transcribe.py speech.mp3")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"Файл не найден: {path}")
        sys.exit(1)

    if not api_key:
        print("Ошибка: в .env не задан VSE_GPT_API")
        sys.exit(1)

    print(f"Транскрибирую: {path}")
    try:
        text = transcribe_voice(path, client)
        print("Результат:")
        print(text)
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)
