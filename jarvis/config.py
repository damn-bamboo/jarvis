"""
Конфигурация ассистента J.A.R.V.I.S.
Правьте config.json (создаётся автоматически), чтобы настроить ассистента под себя —
код менять не нужно. Здесь описаны значения по умолчанию.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Значения по умолчанию (переопределяются файлом config.json)
DEFAULTS = {
    # ---------- Голос (TTS) ----------
    "voice": {
        # Имя голоса из списка pyttsx3. Пусто = первый доступный русский голос.
        # Чтобы получить "голос Джарвиса": установите любой английский мужской голос
        # (например "Microsoft David") и скачайте бесплатный голосовой пакет "Jarvis"
        # с neovoice.ru, затем укажите его имя здесь.
        # Список голосов: python gui.py --list-voices
        "name": "",
        "rate": 175,          # скорость речи (слов/мин), 150~200 — комфортно
        "volume": 1.0,        # 0.0 .. 1.0
    },

    # ---------- Распознавание речи (STT) ----------
    "speech": {
        "language": "ru-RU",     # язык распознавания
        "energy_threshold": 300, # чувствительность микрофона (меньше = чувствительнее)
        "pause_threshold": 0.8,  # сколько секунд тишины = конец фразы
        "keyword": "джарвис",    # слово-активатор
    },

    # ---------- Браузер для Яндекс Музыки и VK ----------
    "browser": {
        "yandex_music_url": "https://music.yandex.ru/home",
        "vk_url": "https://vk.com/audio",
        "search_engine": "https://yandex.ru/search/?text={query}",
    },

    # ---------- Запуск программ: имя в команде -> путь или команда ----------
    # Ассистент понимает: "Джарвис, запусти <ключ>". Добавьте свои ключи!
    "programs": {
        "ворд": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        "эксель": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        "блокнот": "notepad",
        "калькулятор": "calc",
        "хром": "chrome",
        "chrome": "chrome",
        "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "проводник": "explorer",
        "яндекс музыка": "__BROWSER_YANDEX_MUSIC__",   # откроется во встроенном браузере
        "вконтакте": "__BROWSER_VK__",
    },

    # ---------- Выключение компьютера ----------
    "shutdown": {
        "confirm_phrase": "да",   # без подтверждения выключения не будет
        "delay_seconds": 15,      # задержка, чтобы можно было передумать ("джарвис, отмена")
    },

    # ---------- Перемотка видео/музыки ----------
    "seek": {
        "step_seconds": 10,       # шаг перемотки "перемотай вперёд / назад"
        "big_step_seconds": 60,   # "перемотай на минуту"
    },

    # ---------- Поиск треков ВК через Yandex Search API (опционально) ----------
    # Токен: https://cloud.yandex.ru/services/yandex-search-api
    # Без токена ассистент просто откроет страницу поиска VK по названию трека.
    "yandex_search_api_key": "",
}


def load_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # глубокая копия значений по умолчанию
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            _deep_update(cfg, user_cfg)
        except Exception as e:
            print(f"[config] Не удалось прочитать config.json: {e}")
    else:
        save_config(cfg)  # создать файл, чтобы пользователь мог его редактировать
    return cfg


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


def _deep_update(base: dict, extra: dict):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
