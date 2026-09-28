# -*- coding: utf-8 -*-
"""
J.A.R.V.I.S. — подготовка изолированного окружения (запускается из setup.bat).

Никакой Python на компьютере ставить НЕ нужно: этот скрипт скачивает
портативный (переносной) Python 3.12 в папку `python` внутри проекта и
создаёт внутри него виртуальное окружение `.venv`. Все библиотеки Джарвиса
ставятся только туда — системный Python, его версии и пакеты не трогаются.

Сам bootstrap работает стандартными средствами любого Python 3.6+
(даже самого свежего 3.14) и зависимостей не требует.
"""
import os
import ssl
import subprocess
import sys
import tarfile
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
PY_DIR = os.path.join(BASE, "python")          # портативный интерпретатор
VENV_DIR = os.path.join(BASE, ".venv")         # виртуальное окружение Джарвиса

# Портативная сборка Python 3.12 (python-build-standalone). Проверено: архив
# содержит python/python.exe и модуль venv — .venv создаётся без установки.
PY_VERSION = "3.12.14"
PY_BUILD = "20260924"                          # тег релиза на GitHub
ARCH = "x86_64" if sys.maxsize > 2**32 else "i686"
TAR_NAME = f"cpython-{PY_VERSION}+{PY_BUILD}-{ARCH}-pc-windows-msvc-install_only.tar.gz"
DOWNLOAD_URLS = [
    f"https://github.com/astral-sh/python-build-standalone/releases/download/{PY_BUILD}/{TAR_NAME}",
    f"https://github.com/indygreg/python-build-standalone/releases/download/{PY_BUILD}/{TAR_NAME}",
]


def portable_python():
    return os.path.join(PY_DIR, "python.exe")


def venv_python():
    return os.path.join(VENV_DIR, "Scripts", "python.exe")


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl._create_unverified_context()


def download(url, dest):
    print(f"  Скачиваю {os.path.basename(url)[:60]}...")
    req = urllib.request.Request(url, headers={"User-Agent": "jarvis-setup"})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as r, \
            open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct % 10 == 0:
                    print(f"    {pct}%")


def ensure_portable_python():
    """Скачиваем и распаковываем портативный Python (нужен 1 раз)."""
    if os.path.isfile(portable_python()):
        print(f"[1/2] Портативный Python уже здесь: python\\ ({PY_VERSION})")
        return True
    print(f"[1/2] Скачиваю портативный Python {PY_VERSION} (~47 МБ)...")
    print("      Он нужен ТОЛЬКО для Джарвиса и живёт в папке проекта —")
    print("      ваш системный Python и другие программы не меняются.")
    tmp = os.path.join(BASE, "_python_download.tar.gz")
    ok = False
    for url in DOWNLOAD_URLS:
        try:
            download(url, tmp)
            ok = True
            break
        except Exception as e:
            print(f"      Не получилось ({e}), пробую другой адрес...")
    if not ok:
        print("  ОШИБКА: не удалось скачать Python. Проверьте интернет")
        print("  и запустите setup.bat ещё раз (качать повторно не будет).")
        return False
    print("  Распаковываю...")
    with tarfile.open(tmp, "r:gz") as z:
        # filter='data' — безопасная распаковка (Python 3.12+; на старых — без него)
        try:
            z.extractall(BASE, filter="data")     # внутри архива папка python/
        except TypeError:
            z.extractall(BASE)
    try:
        os.remove(tmp)
    except OSError:
        pass
    if not os.path.isfile(portable_python()):
        print("  ОШИБКА: после распаковки не найден python\\python.exe")
        return False
    return True


def ensure_venv():
    """Создаём .venv из портативного Python (если его нет)."""
    if os.path.isfile(venv_python()):
        print("[2/2] Виртуальное окружение .venv уже создано")
        return True
    print("[2/2] Создаю виртуальное окружение .venv...")
    r = subprocess.run([portable_python(), "-m", "venv", VENV_DIR])
    if r.returncode != 0 or not os.path.isfile(venv_python()):
        print("  ОШИБКА: не удалось создать окружение .venv")
        return False
    return True


def main():
    print("=" * 52)
    print(" J.A.R.V.I.S. — подготовка изолированного окружения")
    print("=" * 52)
    if sys.platform != "win32":
        print("Этот скрипт рассчитан на Windows.")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)
    if not ensure_portable_python():
        input("\nНажмите Enter для выхода...")
        sys.exit(1)
    if not ensure_venv():
        input("\nНажмите Enter для выхода...")
        sys.exit(1)
    print("-" * 52)
    print("Окружение готово. Передаю управление установке библиотек...")
    print("-" * 52)
    code = subprocess.call([venv_python(), os.path.join(BASE, "setup.py")])
    sys.exit(code)


if __name__ == "__main__":
    main()
