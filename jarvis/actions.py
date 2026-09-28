"""
Исполнитель команд: запуск программ, письмо в Word, выключение ПК, перемотка.

Все функции возвращают человекочитаемый текст-ответ (его озвучит Voice).
Функции для встроенного браузера (Яндекс Музыка / VK) вызывает GUI —
они помечены specially ("__BROWSER_...") или возвращаются как действия.
"""

import datetime
import os
import subprocess
import threading
import time

# --- необязательные модули: импорт защищён, чтобы код запускался и без них ---
try:
    from pynput.keyboard import Controller as KeyController, Key
    _HAS_KEYBOARD = True
except Exception:
    KeyController = None
    Key = None
    _HAS_KEYBOARD = False

try:
    import pygetwindow as gw
    _HAS_WINDOWS = True
except Exception:
    gw = None
    _HAS_WINDOWS = False


keyboard = KeyController() if _HAS_KEYBOARD else None

# Окна плееров, которые умеем "переключать" перед перемоткой
_PLAYER_HINTS = ["vlc", "potplayer", "mpc", "5klabs", "kmplayer", "gom",
                 "windows media", "mediaplayer", "kodi", "mpv", "shotcut", "premiere"]

# Быстрые клавиши перемотки популярных плееров (заполняются при наличии pynput)
if _HAS_KEYBOARD:
    _SEEK_KEYS = {
        "vlc":       {"back": Key.left, "fwd": Key.right},   # VLC: ← → мотают на 10 с / 1 мин
        "potplayer": {"back": Key.left, "fwd": Key.right},
        "default":   {"back": Key.left, "fwd": Key.right},
    }
else:
    _SEEK_KEYS = {}


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace("ё", "е").split())


# ======================================================================
# 1. ЗАПУСК ПРОГРАММ
# ======================================================================
def launch_program(name: str, cfg: dict) -> str:
    """Запускает программу по ключу из config['programs'] (или через PATH/Пуск)."""
    key = _norm(name)
    programs = { _norm(k): v for k, v in cfg["programs"].items() }

    path = programs.get(key)
    if path is None:
        # нечёткое совпадение: "ворд 2019" -> "ворд"
        for k, v in programs.items():
            if k and (k in key or key in k):
                path = v
                break

    if path is None:
        # пробуем найти ярлык в меню "Пуск"
        found = _search_start_menu(name)
        path = found

    if path is None:
        return f"Программа «{name}» не найдена в списке. Добавьте её в config.json, раздел programs."

    if path == "__BROWSER_YANDEX_MUSIC__":
        return "__OPEN_YANDEX_MUSIC__"
    if path == "__BROWSER_VK__":
        return "__OPEN_VK__"

    try:
        if os.path.exists(path):
            subprocess.Popen([path])
        else:
            subprocess.Popen(path, shell=True)
        return f"Запускаю {name}."
    except Exception as e:
        return f"Не удалось запустить {name}: {e}"


def _search_start_menu(name: str):
    """Ищет .lnk в меню Пуск Windows и возвращает путь к цели (best effort)."""
    if os.name != "nt":
        return None
    name_n = _norm(name)
    roots = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    for root in roots:
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if fn.lower().endswith(".lnk") and name_n in _norm(fn[:-4]):
                    target = _resolve_lnk(os.path.join(dirpath, fn))
                    if target and os.path.exists(target):
                        return target
    return None


def _resolve_lnk(lnk_path: str):
    """Читает путь цели из .lnk через PowerShell (без лишних зависимостей)."""
    try:
        ps = (
            "$s=(New-Object -COM WScript.Shell).CreateShortcut('%s');$s.TargetPath" %
            lnk_path.replace("'", "''")
        )
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=8)
        p = out.stdout.strip()
        return p or None
    except Exception:
        return None


# ======================================================================
# 2. ВЫКЛЮЧЕНИЕ / ПЕРЕЗАГРУЗКА КОМПЬЮТЕРА
# ======================================================================
_pending_shutdown = {"timer": None}


def schedule_shutdown(cfg: dict) -> str:
    """Отложенное выключение: можно передумать командой «отмена»."""
    delay = int(cfg["shutdown"].get("delay_seconds", 15))

    def _do():
        try:
            subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
        except Exception as e:
            print(f"[shutdown] {e}")

    cancel_pending()
    t = threading.Timer(delay, _do)
    t.daemon = True
    t.start()
    _pending_shutdown["timer"] = t
    return f"Выключаю компьютер через {delay} секунд. Скажите «Джарвис, отмена», чтобы передумать."


def cancel_pending() -> str | None:
    t = _pending_shutdown["timer"]
    if t is not None and t.is_alive():
        t.cancel()
        _pending_shutdown["timer"] = None
        if os.name == "nt":
            subprocess.run(["shutdown", "/a"], check=False)
        return "Отменяю выключение. Компьютер остаётся включённым."
    return None


def restart_pc() -> str:
    if os.name == "nt":
        subprocess.run(["shutdown", "/r", "/t", "5"], check=False)
        return "Перезагружаю компьютер через 5 секунд."
    return "Перезагрузка доступна только на Windows."


# ======================================================================
# 3. MICROSOFT WORD — письмо под диктовку
# ======================================================================
def word_write(text: str) -> str:
    """
    Пишет распознанный текст в активный документ Word.
    Вариант А (предпочтительный): COM-интероп через comtypes/pywin32.
    Вариант Б: эмуляция клавиатуры (pynput) — работает с WordPad/Блокнотом тоже.
    """
    if _word_type_via_com(text):
        return "Готово, напечатал в Word."
    # запасной вариант — печатаем клавиатурой в активное окно
    if not _HAS_KEYBOARD:
        return "Не могу писать: установите comtypes и pynput (pip install comtypes pynput)."
    try:
        _activate_any_window_containing(("word", "документ"))
        time.sleep(0.3)
        keyboard.type(text + "\n")
        return "Напечатал текст в активном окне."
    except Exception as e:
        return f"Ошибка ввода текста: {e}"


def _word_type_via_com(text: str) -> bool:
    try:
        import comtypes.client  # noqa
    except Exception:
        return False
    try:
        word = comtypes.client.GetActiveObject("Word.Application")
        doc = word.ActiveDocument
        sel = word.Selection
        sel.TypeText(text + "\n")
        return True
    except Exception:
        return False


# ======================================================================
# 4. ПЕРЕМОТКА ВИДЕО В ЛЮБОМ ПЛЕЕРЕ / БРАУЗЕРЕ
# ======================================================================
def seek_media(direction: str, seconds: int | None = None, cfg: dict | None = None) -> str:
    """
    direction: 'forward' | 'backward'.
    Переключается на окно плеера (если найдено) и шлёт клавиши перемотки.
    Для браузеров (YouTube, VK видео) работают те же стрелки ← →,
    если видео активно (клик по видео делает GUI либо пользователь).
    """
    cfg = cfg or {}
    seek_cfg = cfg.get("seek", {}) or {}
    step = int(seek_cfg.get("step_seconds", 10)) or 10
    big_step = int(seek_cfg.get("big_step_seconds", 60)) or 60

    if seconds is None:
        seconds = step
    presses = max(1, round(seconds / step))

    if not _HAS_KEYBOARD:
        return "Перемотка недоступна: установите pynput."

    focused = _current_window_title().lower()
    is_player = any(h.strip() in focused for h in _PLAYER_HINTS)
    if not is_player:
        # пытаемся найти окно плеера и активировать его
        for hint in ("vlc", "potplayer", "mpc", "media player", "mpv"):
            if _activate_any_window_containing((hint,)):
                is_player = True
                break

    key = "fwd" if direction == "forward" else "back"

    try:
        kb = _SEEK_KEYS.get(_which_player(focused), _SEEK_KEYS["default"])
        # Если просят перемотать на крупный шаг (минута и больше) — используем
        # клавишу Alt-стрелка там, где это поддерживается, иначе много нажатий.
        use_big = seconds >= big_step
        for _ in range(1 if use_big else presses):
            if use_big:
                with keyboard.pressed(Key.alt):
                    keyboard.press(kb[key]); keyboard.release(kb[key])
            else:
                keyboard.press(kb[key]); keyboard.release(kb[key])
            time.sleep(0.05)
        where = "в плеере" if is_player else "в активном окне"
        n = seconds if use_big else presses * step
        return f"Перемотал {'вперёд' if direction=='forward' else 'назад'} примерно на {n} секунд {where}."
    except Exception as e:
        return f"Не удалось перемотать: {e}"


def _which_player(title_lower: str) -> str:
    for name in ("vlc", "potplayer", "mpc"):
        if name in title_lower:
            return name
    return "default"


def _current_window_title() -> str:
    if not _HAS_WINDOWS:
        return ""
    try:
        w = gw.getActiveWindow()
        return w.title if w else ""
    except Exception:
        return ""


def _activate_any_window_containing(substrings) -> bool:
    if not _HAS_WINDOWS:
        return False
    try:
        for t in gw.getAllTitles():
            low = _norm(t)
            if any(s in low for s in substrings):
                win = gw.getWindowsWithTitle(t)
                if win:
                    win[0].activate()
                    time.sleep(0.2)
                    return True
    except Exception:
        pass
    return False


# ======================================================================
# 5. МЕЛОЧИ: время, дата
# ======================================================================
def answer_small_talk(text: str) -> str | None:
    t = _norm(text)
    if "который час" in t or "сколько времени" in t:
        return "Сейчас " + datetime.datetime.now().strftime("%H:%M") + "."
    if "какое сегодня число" in t or "какой сегодня день" in t:
        return "Сегодня " + datetime.datetime.now().strftime("%d.%m.%Y") + "."
    return None
