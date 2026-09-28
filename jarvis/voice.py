"""
Голосовой синтез (TTS) через pyttsx3 — работает офлайн, через системные голосовые движки.

На Windows используется SAPI5: любой установленный голос (в т.ч. скачанный "Jarvis"
с neovoice.ru или Microsoft David) доступен здесь по имени.

Голос Джарвиса в Marvel говорит по-английски, поэтому обычно делают так:
  - русский текст -> перевод на английский (опционально) -> голос Jarvis;
либо просто берут русский мужской голос и понижают скорость/тон.
Здесь реализован второй, простой вариант + поддержка любого голоса из config.json.
"""

import threading

try:
    import pyttsx3
    _HAS_TTS = True
except Exception:          # чтобы демо/тесты работали и без установленного pyttsx3
    pyttsx3 = None
    _HAS_TTS = False


class Voice:
    def __init__(self, voice_cfg: dict):
        self.cfg = voice_cfg
        self._lock = threading.Lock()   # pyttsx3 не потокобезопасен

    def _build_engine(self):
        engine = pyttsx3.init()
        engine.setProperty("rate", int(self.cfg.get("rate", 175)))
        engine.setProperty("volume", float(self.cfg.get("volume", 1.0)))

        wanted = (self.cfg.get("name") or "").strip().lower()
        if wanted:
            for v in engine.getProperty("voices"):
                haystack = " ".join([v.name or "", getattr(v, "id", "") or ""]).lower()
                if wanted in haystack:
                    engine.setProperty("voice", v.id)
                    break
        return engine

    def say(self, text: str):
        """Произносит текст (блокирующе — вызывайте из рабочего потока)."""
        if not text:
            return
        if not _HAS_TTS:
            print(f"[джарвис] {text}")
            return
        with self._lock:
            try:
                engine = self._build_engine()
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"[tts] Ошибка озвучки: {e}")

    @staticmethod
    def list_voices():
        """Печатает все доступные голоса — чтобы выбрать 'голос Джарвиса'."""
        if not _HAS_TTS:
            print("[tts] pyttsx3 не установлен (pip install pyttsx3) — список голосов недоступен.")
            return
        try:
            engine = pyttsx3.init()
            print("Доступные голоса:")
            for i, v in enumerate(engine.getProperty("voices")):
                print(f"  [{i}] {v.name}   (id: {v.id})")
            engine.stop()
        except Exception as e:
            print(f"[tts] Не удалось получить список голосов: {e}")
