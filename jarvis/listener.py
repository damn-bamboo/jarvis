"""
Слушатель речи: микрофон -> текст.

Два режима:
 1) constantly_listening() — постоянный поток распознанных фраз (для слова-активатора);
 2) listen_once(timeout)   — одна фраза (используется, когда ассистент уже "разбужен").

Используется SpeechRecognition + Google Web Speech API (бесплатно, нужен интернет).
Если интернета нет — можно подключить Vosk (см. README, раздел "Офлайн-распознавание").
"""

import queue
import threading

import speech_recognition as sr


class SpeechListener:
    def __init__(self, language="ru-RU", energy_threshold=300, pause_threshold=0.8):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = pause_threshold
        self._stop_event = threading.Event()
        # pyaudio может отсутствовать (например, на Python 3.14) — не падаем:
        # просто микрофон будет недоступен, используйте текстовый режим.
        try:
            sr.Microphone()
            self.mic_available = True
        except Exception:
            self.mic_available = False
            print("[mic] Микрофон недоступен (не установлен pyaudio или нет устройства). "
                  "Работает текстовый ввод: python gui.py --text-only")

    # ------------------------------------------------------------------
    def listen_once(self, timeout=None, phrase_time_limit=8):
        """Слушает микрофон и возвращает распознанный текст (или '')."""
        if not getattr(self, "mic_available", True):
            return ""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self.recognizer.listen(source, timeout=timeout,
                                               phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return ""
        except OSError as e:
            print(f"[mic] Ошибка микрофона: {e}")
            return ""

        try:
            # Google Web Speech — хорошо понимает русский
            return self.recognizer.recognize_google(audio, language=self.language).lower()
        except sr.UnknownValueError:
            return ""            # речь не распознана
        except sr.RequestError as e:
            print(f"[stt] Нет связи с сервисом распознавания: {e}")
            return ""
        except Exception as e:
            print(f"[stt] {e}")
            return ""

    # ------------------------------------------------------------------
    def constantly_listening(self, out_queue: "queue.Queue[str]"):
        """Фоновый поток: кладёт все распознанные фразы в out_queue."""
        self._stop_event.clear()

        def _worker():
            while not self._stop_event.is_set():
                text = self.listen_once(timeout=None, phrase_time_limit=6)
                if text:
                    out_queue.put(text)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t

    def stop(self):
        self._stop_event.set()
