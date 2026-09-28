# -*- coding: utf-8 -*-
"""
J.A.R.V.I.S. — установка библиотек (вызывается bootstrap.py внутри .venv).

Окружение (портативный Python + .venv) уже готово — здесь ставятся только
пакеты Джарвиса. Работает на Python 3.8–3.13; pyaudio берётся из готовых
бинарных wheel с PyPI (компилятор не нужен).
"""
import os
import platform
import re
import subprocess
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))

LIBS = ["SpeechRecognition", "pyttsx3", "pynput", "pygetwindow",
        "psutil", "requests", "comtypes", "PyQt6", "PyQt6-WebEngine"]

# Готовые бинарные сборки pyaudio (не нужен компилятор)
PYAUDIO_WHEELS_URL = "https://api.github.com/repos/intxcc/pyaudio_portaudio/releases"


def run(args, **kw):
    return subprocess.run(args, **kw)


def pip_install(pkgs):
    return run([sys.executable, "-m", "pip", "install", *pkgs]).returncode == 0


def have_pyaudio():
    try:
        import pyaudio  # noqa: F401
        return True
    except Exception:
        return False


def install_pyaudio_binary():
    """Запасной способ: готовые wheels pyaudio с GitHub (для старых Python)."""
    vi = sys.version_info
    tag = f"cp{vi.major}{vi.minor}"                      # напр. cp312
    arch = "win_amd64" if platform.architecture()[0] == "64bit" else "win32"
    print(f"Ищу готовый wheel pyaudio для {tag} ({arch})...")
    try:
        req = urllib.request.Request(PYAUDIO_WHEELS_URL,
                                     headers={"User-Agent": "jarvis-setup"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read().decode("utf-8")
        urls = re.findall(r'"browser_download_url"\s*:\s*"([^"]+\.whl)"', data)
        wheel = next((u for u in urls if tag in u and arch in u), None)
        if not wheel:
            print("  Подходящий wheel не найден.")
            return False
        print(f"  Скачиваю: {wheel.split('/')[-1]}")
        dest = os.path.join(BASE, wheel.split("/")[-1])
        urllib.request.urlretrieve(wheel, dest)
        ok = pip_install([dest])
        try:
            os.remove(dest)
        except OSError:
            pass
        return ok
    except Exception as e:
        print(f"  Не получилось ({e}).")
        return False


def main():
    print("=" * 52)
    print(" J.A.R.V.I.S. — установка библиотек в .venv")
    print("=" * 52)

    vi = sys.version_info
    print(f"Python окружения: {sys.version.split()[0]}  ({platform.architecture()[0]}, {platform.system()})")
    if (vi.major, vi.minor) < (3, 8):
        print("Слишком старый Python (нужен 3.8+). Удалите папки python и .venv,")
        print("затем запустите setup.bat заново.")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)
    if (vi.major, vi.minor) >= (3, 14):
        print()
        print("ВНИМАНИЕ: этому окружению достался Python 3.14+ — для него пока")
        print("НЕТ готовых сборок pyaudio (микрофон). Остальное установится,")
        print("но если хотите голосовой ввод, удалите папки `python` и `.venv`")
        print("в проекте и запустите setup.bat заново — он скачает правильный")
        print("портативный Python 3.12.")
        print("Продолжаю установку остальных компонентов...\n")

    print("[1/3] Обновляю pip...")
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])

    print("[2/3] Ставлю библиотеки (нужен интернет, 3-5 минут)...")
    if not pip_install(LIBS):
        print("Часть библиотек не установилась — проверьте интернет и повторите.")

    print("[3/3] Ставлю pyaudio (микрофон)...")
    if have_pyaudio():
        print("  pyaudio уже установлен, пропускаю.")
    else:
        quiet = run([sys.executable, "-m", "pip", "install", "pyaudio",
                     "--disable-pip-version-check"])
        if quiet.returncode != 0 or not have_pyaudio():
            print("  Обычная установка не удалась — пробую готовые wheels с GitHub...")
            if not install_pyaudio_binary():
                print("  И этот способ не сработал. См. README -> 'Не ставится pyaudio'.")

    print()
    print("=" * 52)
    if have_pyaudio():
        print(" ГОТОВО! Микрофон (pyaudio) установлен.")
    else:
        print(" УСТАНОВЛЕНО ЧАСТИЧНО:")
        print(" интерфейс, голос и команды работают; микрофон — нет.")
        print(" Как довести pyaudio — см. README.")
    print(" Запуск: двойной клик на start.bat")
    print(" Настройки: config.json или кнопка в окне")
    print("=" * 52)
    input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    main()
