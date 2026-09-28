"""
Поиск музыкальных треков: Яндекс Музыка (программа на ПК / сайт) -> VK (браузер).

Логика по ТЗ:
  «Джарвис, включи <трек>» ->
    1) пробуем найти трек в Яндекс Музыке;
    2) если не нашли — открываем поиск этого трека ВКонтакте в браузере.

Яндекс Музыка официально не даёт внешнего API управления десктоп-приложением,
поэтому "проверка наличия" делается через открытый API поиска Яндекс Music
(https://music.yandex.ru) — он возвращает JSON для незалогиненных запросов.
Если трек найден — ассистент открёт встроенный браузер на странице трека и
попросит нажать «воспроизвести» (или сам кликнет кнопкой Play/Pause, см. GUI).
Если не найден — строится ссылка на поиск VK: https://vk.com/search?section=audio&q=...
"""

import re
import urllib.parse

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False


# ---------- Очистка названия трека из распознанной речи ----------
_NOISE_WORDS = [
    "включи", "запусти", "играй", "поставь", "трек", "музыку", "музыка",
    "песню", "песня", "композицию", "альбом", "исполнителя", "группу",
    "джарвис", "пожалуйста", "мне", "напиши",
]


def clean_track_query(text: str) -> str:
    t = text.lower().replace("ё", "е")
    for w in _NOISE_WORDS:
        t = t.replace(w, "")
    t = re.sub(r"[^\w\s\-&.+]", " ", t, flags=re.UNICODE)
    return " ".join(t.split())


# ---------- Поиск в Яндекс Музыке ----------
YM_SEARCH_URL = "https://music.yandex.ru/handlers/search.jsx"


def yandex_music_find(query: str) -> dict | None:
    """
    Ищет трек в Яндекс Музыке через веб-обработчик search.jsx.
    Возвращает {"title","artist","id","url"} или None, если не найдено/нет сети.
    Примечание: это неофициальный эндпоинт — при изменении Яндексом используйте
    официальный Яндекс.Музыка API (нужен OAuth-токен, см. README).
    """
    if not _HAS_REQUESTS or not query:
        return None
    try:
        r = requests.get(YM_SEARCH_URL,
                         params={"text": query, "type": "track", "limit": 5},
                         timeout=8,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return None
        data = r.json()
        tracks = data.get("tracks") or []
        if not tracks:
            # иногда ответ лежит в result.tracks
            res = data.get("result") or {}
            tracks = res.get("tracks") or []
        if not tracks:
            return None
        best = tracks[0]
        artists = ", ".join(a.get("name", "") for a in best.get("artists", []) or [])
        album = best.get("album", {}).get("title", "") if isinstance(best.get("album"), dict) else ""
        tid = best.get("id")
        album_id = best.get("albumId") or (best.get("album", {}) or {}).get("id", "")
        url = f"https://music.yandex.ru/album/{album_id}/track/{tid}"
        return {
            "title": best.get("title", query),
            "artist": artists,
            "album": album,
            "id": tid,
            "url": url,
        }
    except Exception as e:
        print(f"[ym] Поиск не удался: {e}")
        return None


# ---------- Ссылка на поиск трека ВК ----------
def vk_search_url(query: str) -> str:
    q = urllib.parse.quote_plus(query)
    return f"https://vk.com/search?section=audio&q={q}"


def yandex_music_search_url(query: str) -> str:
    q = urllib.parse.quote_plus(query)
    return f"https://music.yandex.ru/search?text={q}"


# ---------- Основная функция выбора источника ----------
def resolve_track(query: str) -> tuple[str, str]:
    """
    Возвращает (source, url):
      source: 'yandex' | 'vk'
      url:    адрес страницы трека/поиска для открытия во встроенном браузере.
    """
    found = yandex_music_find(query)
    if found:
        return "yandex", found["url"]
    return "vk", vk_search_url(query)
