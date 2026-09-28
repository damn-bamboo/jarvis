"""
Разбор распознанной речи на команды.

Вход: текст вида "джарвис выключи компьютер", "перемотай видео назад на минуту".
Выход: Command(name, argument) — имя команды и аргумент для исполнителя.

Команды (легко расширять в COMMAND_PATTERNS):
  wake            - просто разбужен словом "Джарвис"
  launch          - запуск программы
  dictation       - письмо в Word ("напиши в ворде ...")
  shutdown        - выключение ПК
  cancel_shutdown - отмена выключения
  restart         - перезагрузка
  seek_forward    / seek_backward - перемотка (+секунды, если названы)
  play_track      - включить трек (Яндекс Музыка -> VK)
  pause           / resume / next_track / prev_track - управление воспроизведением
  volume_up/down/mute
  open_yandex_music / open_vk
  time / date
  exit            - свернуть/остановить ассистента
  unknown
"""

import re
from dataclasses import dataclass

_NUM_WORDS = {
    "одну": 1, "одного": 1, "один": 1, "две": 2, "двух": 2, "три": 3, "четыре": 4,
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
    "пятнадцать": 15, "двадцать": 20, "полминуты": 30, "минуту": 60, "минуты": 120,
}


@dataclass
class Command:
    name: str
    argument: str = ""
    seconds: int = 0


def _norm(text: str) -> str:
    return " ".join((text or "").lower().replace("ё", "е").split())


def _strip_wake(text: str, keyword: str) -> str:
    """Убирает слово-активатор из начала/середины фразы."""
    t = _norm(text)
    kw = keyword.lower().replace("ё", "е")
    variants = [kw, f"привет {kw}", f"ой {kw}", f"{kw},"]
    for v in variants:
        if t.startswith(v):
            t = t[len(v):]
            break
    else:
        t = re.sub(rf"\b{re.escape(kw)}\b", "", t, count=1).strip()
    return t.strip(" ,.")


# ---------- Вспомогательные извлечения ----------
def _extract_seconds(t: str) -> int:
    m = re.search(r"(\d+)\s*(сек|с\b)", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*(минут)", t)
    if m:
        return int(m.group(1)) * 60
    for word, val in _NUM_WORDS.items():
        if f"{word} секунд" in t:
            return val
        if f"{word} минут" in t:
            return val * 60
    if re.search(r"\b(минуту|полминуты)\b", t):
        return 60 if "минуту" in t else 30
    return 0


def _cut_first(patterns, t: str):
    """Если фраза начинается с одного из паттернов — возвращает остаток."""
    for p in patterns:
        m = re.match(p, t)
        if m:
            return t[m.end():].strip()
    return None


# ---------- Основной разбор ----------
def parse(text: str, wake_keyword: str = "джарвис") -> Command:
    raw = _norm(text)
    t = _strip_wake(raw, wake_keyword)

    # Разбужен без команды?
    if not t or t == wake_keyword:
        return Command("wake")

    # ---- Выключение / перезагрузка / отмена ----
    if re.search(r"(выключи|отключи|погаси|заверш|shutdown).*(комп|пк|эвм|систем|computer)", t) \
       or t in ("выключись", "выключайся"):
        return Command("shutdown")
    if re.search(r"(отмен|прекрат|не надо|передумал|стоп выключени)", t):
        return Command("cancel_shutdown")
    if re.search(r"перезагруз", t):
        return Command("restart")

    # ---- Диктовка в Word ----
    arg = _cut_first([r"напиши\s+(в\s+)?(ворде|word)?\s*[:]?\s*",
                      r"напечатать\s*[:]?\s*", r"текст\s*[:]?\s*",
                      r"диктуй\s*[:]?\s*"], t)
    if arg is not None and ("ворд" in t or "word" in t or len(arg) > 2):
        return Command("dictation", argument=arg or t)

    # ---- Перемотка ----
    if re.search(r"(перемот|промот|мотай|вперёд|назад|forward|rewind|skip)", t):
        secs = _extract_seconds(t)
        back = bool(re.search(r"(назад|rewind|back|против)", t))
        fwd = bool(re.search(r"(вперёд|вперед|forward|next|дальше)", t))
        if back and not fwd:
            return Command("seek_backward", seconds=secs)
        return Command("seek_forward", seconds=secs)

    # ---- Управление воспроизведением ----
    if re.fullmatch(r"(пауза|приостанови|стоп|замри)", t):
        return Command("pause")
    if re.search(r"(продолжи|возобнови|играй дальше|продолжай)", t):
        return Command("resume")
    if re.search(r"(следующ(ий|ая|ое) (трек|песня)|дальше трек|скипни|пропусти трек)", t):
        return Command("next_track")
    if re.search(r"(предыдущ(ий|ая|ое) (трек|песня)|верни трек назад|назад к предыдущ)", t):
        return Command("prev_track")
    if re.search(r"(громче|прибавь громкост|увеличь громкост)", t):
        return Command("volume_up")
    if re.search(r"(тише|убавь громкост|уменьши громкост)", t):
        return Command("volume_down")
    if re.search(r"(без звука|выключи звук|mute|тишина)", t):
        return Command("volume_mute")

    # ---- Открыть/запустить сервисы (проверяется ДО запуска программ и треков) ----
    if re.search(r"(открой|запусти|включи).*(яндекс музыка|яндекс музыку|музыку яндекса)", t) \
       or t in ("яндекс музыка",):
        return Command("open_yandex_music")
    if re.search(r"(открой|запусти|включи).*(в контакте|вконтакте|\bvk\b|в к\b)", t) or t in ("вконтакте", "vk"):
        return Command("open_vk")

    # ---- Включить трек: «включи/поставь/играй [трек|песню] <название>» ----
    m = re.search(r"^(включи|запусти|поставь|играй|давай)\s+(трек\s+|песню\s+|песня\s+|композицию\s+)?(.+)", t)
    if m and len(m.group(3).split()) >= 2:   # название из 2+ слов — почти наверняка трек
        return Command("play_track", argument=m.group(3).strip())

    # ---- Запуск программы: короткое имя из списка config['programs'] ----
    arg = _cut_first([r"запусти\s+(программу\s+|приложение\s+|игру\s+)?",
                      r"открой\s+(программу\s+|приложение\s+|игру\s+)?",
                      r"включи\s+(программу\s+)?"], t)
    if arg and len(arg.split()) <= 3:   # короткие названия = программы, длинные = треки
        return Command("launch", argument=arg)

    # ---- Одиночное слово после «включи/поставь» — тоже считаем треком ----
    if m:
        return Command("play_track", argument=m.group(3).strip())

    # ---- Время / дата ----
    if re.search(r"(который час|сколько времени|время)", t):
        return Command("time")
    if re.search(r"(какое сегодня число|какой сегодня день|какая дата)", t):
        return Command("date")

    # ---- Выход ----
    if re.search(r"(выход|выключись|отключись|спокойной ночи|до свидания|пока)", t):
        return Command("exit")

    return Command("unknown", argument=t)
