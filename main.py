"""
Запасной режим без графического интерфейса: консоль + голос.

  python main.py            — голосовой режим (говорите «Джарвис, …»)
  python main.py --demo     — демо-разбор команд без микрофона и динамиков

Ссылки на Яндекс Музыку/VK в этом режиме открываются в обычном браузере системы.
"""

import sys
import webbrowser

from jarvis.assistant import Assistant
from jarvis.parser import parse


DEMO_PHRASES = [
    "джарвис который час",
    "джарвис запусти блокнот",
    "джарвис напиши в ворде привет это тест диктовки",
    "джарвис перемотай видео назад",
    "джарвис перемотай на минуту вперёд",
    "джарвис включи летова звук имени",
    "джарвис пауза",
    "джарвис выключи компьютер",
    "джарвис отмена",
    "джарвис пока",
]


def run_demo():
    print("=== Демон разбора команд (действия не выполняются) ===")
    for phrase in DEMO_PHRASES:
        c = parse(phrase)
        print(f"«{phrase}»  ->  {c.name} | arg={c.argument!r} | sec={c.seconds}")


def run_voice():
    a = Assistant()
    a.on_heard = lambda t: print(f"[вы]      {t}")
    a.on_reply = lambda t: print(f"[джарвис] {t}")
    a.on_open_url = lambda u: webbrowser.open(u)
    a.start()
    print("Ассистент слушает. Скажите «Джарвис», затем команду. Ctrl+C — выход.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        a.stop()
        print("\nОстановлено.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_voice()
