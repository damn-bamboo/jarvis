"""
Мозг ассистента: очередь фраз -> разбор -> выполнение -> голосовой ответ.

Потоки:
  _listen_thread  — слушает микрофон постоянно; пока ассистент "спит", ждёт слово-активатор;
                    когда разбужен — передаёт все фразы в обработчик и через N секунд снова засыпает.
  _work_thread    — берёт команды, выполняет (actions/music) и озвучивает ответы.

GUI (gui.py) общается с Assistant через сигналы-колбэки: on_state, on_heard, on_reply, on_open_url.
"""

import queue
import threading
import time

from . import actions, music
from .config import load_config
from .listener import SpeechListener
from .parser import parse, Command
from .voice import Voice


class Assistant:
    AWAKE_WINDOW = 8.0   # секунд, в течение которых ассистент слушает команды без активатора

    def __init__(self):
        self.cfg = load_config()
        sp = self.cfg["speech"]
        self.listener = SpeechListener(sp["language"], sp["energy_threshold"], sp["pause_threshold"])
        self.voice = Voice(self.cfg["voice"])
        self.wake_kw = sp["keyword"]

        self._q: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()
        self.awake = False
        self._last_awake_ts = 0.0

        # колбэки для GUI
        self.on_state = lambda s: None      # 'sleeping' | 'awake' | 'listening' | 'thinking' | 'speaking'
        self.on_heard = lambda t: None      # распознанный текст
        self.on_reply = lambda t: None      # ответ ассистента (текст)
        self.on_open_url = lambda url: None # открыть URL во встроенном браузере

    # ------------------------------------------------------------------
    def start(self):
        threading.Thread(target=self._listen_thread, daemon=True).start()
        threading.Thread(target=self._work_thread, daemon=True).start()
        self._set_state("sleeping")

    def stop(self):
        self._stop.set()
        self.listener.stop()

    def _set_state(self, s):
        try:
            self.on_state(s)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _listen_thread(self):
        while not self._stop.is_set():
            text = self.listener.listen_once(timeout=None, phrase_time_limit=10)
            if not text:
                # если проспали окно ожидания — снова засыпаем
                if self.awake and time.time() - self._last_awake_ts > self.AWAKE_WINDOW:
                    self.awake = False
                    self._set_state("sleeping")
                continue

            self.on_heard(text)
            cmd = parse(text, self.wake_kw)

            woke_by_keyword = wake_detected(text, self.wake_kw)
            if self.awake or woke_by_keyword:
                self.awake = True
                self._last_awake_ts = time.time()
                self._set_state("awake")
                self._q.put(text)
            # иначе — игнорируем фон (не сказали "Джарвис")

    # ------------------------------------------------------------------
    def _work_thread(self):
        while not self._stop.is_set():
            try:
                text = self._q.get(timeout=0.3)
            except queue.Empty:
                continue

            self._set_state("thinking")
            cmd = parse(text, self.wake_kw)
            reply = self._execute(cmd)

            if reply == "__OPEN_YANDEX_MUSIC__":
                reply = "Открываю Яндекс Музыку."
                self._safe_open(self.cfg["browser"]["yandex_music_url"])
            elif reply == "__OPEN_VK__":
                reply = "Открываю ВКонтакте."
                self._safe_open(self.cfg["browser"]["vk_url"])

            self.on_reply(reply)
            self._set_state("speaking")
            self.voice.say(reply)
            self._set_state("awake" if self.awake else "sleeping")

    # ------------------------------------------------------------------
    def _execute(self, cmd: Command) -> str:
        name = cmd.name

        if name == "wake":
            return "Слушаю вас."
        if name == "launch":
            return actions.launch_program(cmd.argument, self.cfg)
        if name == "dictation":
            return actions.word_write(cmd.argument)
        if name == "shutdown":
            return actions.schedule_shutdown(self.cfg)
        if name == "cancel_shutdown":
            r = actions.cancel_pending()
            return r or "Отменять нечего, выключение не запланировано."
        if name == "restart":
            return actions.restart_pc()
        if name == "seek_forward":
            return actions.seek_media("forward", cmd.seconds or None, self.cfg)
        if name == "seek_backward":
            return actions.seek_media("backward", cmd.seconds or None, self.cfg)
        if name in ("pause", "resume", "next_track", "prev_track"):
            return self._media_key(name)
        if name in ("volume_up", "volume_down", "volume_mute"):
            return self._volume(name)
        if name == "play_track":
            return self._play_track(cmd.argument)
        if name == "open_yandex_music":
            self._safe_open(self.cfg["browser"]["yandex_music_url"])
            return "Открываю Яндекс Музыку."
        if name == "open_vk":
            self._safe_open(self.cfg["browser"]["vk_url"])
            return "Открываю ВКонтакте."
        if name == "time":
            return actions.answer_small_talk("который час") or ""
        if name == "date":
            return actions.answer_small_talk("какое сегодня число") or ""
        if name == "exit":
            self.awake = False
            return "До свидания. Сплю до следующего вызова."
        # unknown
        small = actions.answer_small_talk(cmd.argument)
        if small:
            return small
        return f"Команда не распознана: «{cmd.argument}». Формулировки команд есть в README."

    # ------------------------------------------------------------------
    def _play_track(self, query: str) -> str:
        q = music.clean_track_query(query) or query
        source, url = music.resolve_track(q)
        if source == "yandex":
            self._safe_open(url)
            return f"Нашёл «{q}» в Яндекс Музыке, открываю трек. Скажите «пауза», чтобы остановить."
        else:
            self._safe_open(url)
            return f"В Яндекс Музыке трек «{q}» не найден. Ищу его ВКонтакте."

    def _media_key(self, name: str) -> str:
        ok = actions._HAS_KEYBOARD
        if not ok:
            return "Управление плеером недоступно: установите pynput."
        from pynput.keyboard import Key
        mapping = {
            "pause": Key.media_play_pause,
            "resume": Key.media_play_pause,
            "next_track": Key.media_next_track,
            "prev_track": Key.media_previous_track,
        }
        try:
            k = mapping[name]
            actions.keyboard.press(k); actions.keyboard.release(k)
            return {"pause": "Пауза.", "resume": "Продолжаю воспроизведение.",
                    "next_track": "Следующий трек.", "prev_track": "Предыдущий трек."}[name]
        except Exception as e:
            return f"Не удалось управлять воспроизведением: {e}"

    def _volume(self, name: str) -> str:
        if not actions._HAS_KEYBOARD:
            return "Регулировка громкости недоступна: установите pynput."
        from pynput.keyboard import Key
        keymap = {"volume_up": Key.media_volume_up,
                  "volume_down": Key.media_volume_down,
                  "volume_mute": Key.media_volume_mute}
        try:
            k = keymap[name]
            reps = 5 if name != "volume_mute" else 1
            for _ in range(reps):
                actions.keyboard.press(k); actions.keyboard.release(k)
                time.sleep(0.02)
            return {"volume_up": "Громче.", "volume_down": "Тише.", "volume_mute": "Без звука."}[name]
        except Exception as e:
            return f"Ошибка регулировки громкости: {e}"

    def _safe_open(self, url: str):
        try:
            self.on_open_url(url)
        except Exception as e:
            print(f"[gui] Не удалось открыть URL: {e}")


def wake_detected(text: str, keyword: str) -> bool:
    t = (text or "").lower().replace("ё", "е")
    kw = keyword.lower().replace("ё", "е")
    return kw in t
