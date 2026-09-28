"""
J.A.R.V.I.S. — голосовой ассистент (интерфейс).

Запуск:            python gui.py
Проверить голоса:  python gui.py --list-voices
Текстовый режим (без микрофона, для отладки): python gui.py --text-only

Что внутри:
  • Круглая "реактор"-анимация состояния (спит / слушает / думает / говорит) — как у Джарвиса;
  • Лента диалога (что услышано / что ответил);
  • Встроенный браузер (вкладки Яндекс Музыка и VK) — команды «включи трек» открываются здесь;
  • Панель настроек: скорость речи, громкость, имя голоса, слово-активатор — всё сохраняется в config.json.
"""

import sys
import threading

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QTabWidget,
    QFormLayout, QSlider, QComboBox, QPlainTextEdit, QDialog, QSizePolicy,
)

from jarvis.assistant import Assistant
from jarvis.config import load_config, save_config
from jarvis.voice import Voice

# WebEngine опционален: если не установлен — работает без встроенного браузера
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    _HAS_WEB = True
except Exception:
    _HAS_WEB = False


STATE_TEXT = {
    "sleeping": "Сплю. Скажите «Джарвис»",
    "awake": "Слушаю…",
    "listening": "Слушаю…",
    "thinking": "Думаю…",
    "speaking": "Говорю…",
}


# ----------------------------------------------------------------------
#  Круглый "реактор" — анимированный индикатор состояния
# ----------------------------------------------------------------------
class ReactorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.state = "sleeping"
        self._angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def set_state(self, s):
        self.state = s

    def _tick(self):
        speed = {"sleeping": 1, "awake": 2, "listening": 3, "thinking": 4, "speaking": 6}.get(self.state, 2)
        self._angle = (self._angle + speed) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = min(self.width(), self.height()) - 20
        rect = QRectF((self.width() - size) / 2, (self.height() - size) / 2, size, size)

        color = {"sleeping": QColor("#7a5b00"), "awake": QColor("#39c5bb"),
                 "listening": QColor("#39c5bb"), "thinking": QColor("#f0a500"),
                 "speaking": QColor("#ffffff")}.get(self.state, QColor("#39c5bb"))

        # свечение в центре
        grad = QRadialGradient(rect.center(), size / 2)
        c = QColor(color); c.setAlpha(120)
        grad.setColorAt(0.0, c)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(rect.centered(QRectF(0, 0, size * 0.5, size * 0.5)))

        # кольца
        for i, frac in enumerate((1.0, 0.82, 0.64)):
            r = rect.adjusted(size * (1 - frac) / 2, size * (1 - frac) / 2,
                              -size * (1 - frac) / 2, -size * (1 - frac) / 2)
            pen = QPen(color, 2 if i else 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            start = (self._angle * (1 + i)) % 360
            span = 300 - i * 40 if self.state != "sleeping" else 120
            p.drawArc(r, int(start * 16), int(span * 16))

        # центральный круг
        core = rect.adjusted(size * 0.38, size * 0.38, -size * 0.38, -size * 0.38)
        p.setPen(QPen(color, 2))
        p.setBrush(QColor(10, 15, 20))
        p.drawEllipse(core)


# ----------------------------------------------------------------------
#  Диалог настроек
# ----------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Настройки J.A.R.V.I.S.")
        self.resize(420, 320)
        form = QFormLayout(self)

        self.name_edit = QLineEdit(cfg["speech"].get("keyword", "джарвис"))
        form.addRow("Слово-активатор:", self.name_edit)

        self.voice_combo = QComboBox()
        try:
            import pyttsx3
            eng = pyttsx3.init()
            for v in eng.getProperty("voices"):
                self.voice_combo.addItem(v.name, v.id)
            eng.stop()
        except Exception:
            self.voice_combo.addItem("(системный по умолчанию)", "")
        cur = cfg["voice"].get("name", "")
        idx = self.voice_combo.findText(cur)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)
        form.addRow("Голос:", self.voice_combo)

        self.rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rate_slider.setRange(80, 300)
        self.rate_slider.setValue(int(cfg["voice"].get("rate", 175)))
        self.rate_lbl = QLabel(str(self.rate_slider.value()))
        self.rate_slider.valueChanged.connect(lambda v: self.rate_lbl.setText(str(v)))
        row = QHBoxLayout(); row.addWidget(self.rate_slider); row.addWidget(self.rate_lbl)
        form.addRow("Скорость речи:", row)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(int(float(cfg["voice"].get("volume", 1.0)) * 100))
        form.addRow("Громкость голоса:", self.vol_slider)

        btn = QPushButton("Сохранить")
        btn.clicked.connect(self._save)
        form.addRow(btn)

    def _save(self):
        self.cfg["speech"]["keyword"] = self.name_edit.text().strip() or "джарвис"
        self.cfg["voice"]["name"] = self.voice_combo.currentText()
        self.cfg["voice"]["rate"] = self.rate_slider.value()
        self.cfg["voice"]["volume"] = self.vol_slider.value() / 100.0
        save_config(self.cfg)
        self.accept()


# ----------------------------------------------------------------------
#  Главное окно
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):
    sig_state = pyqtSignal(str)
    sig_heard = pyqtSignal(str)
    sig_reply = pyqtSignal(str)
    sig_open_url = pyqtSignal(str)

    def __init__(self, text_only=False):
        super().__init__()
        self.text_only = text_only
        self.setWindowTitle("J.A.R.V.I.S. — голосовой ассистент")
        self.resize(1100, 700)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #0b1220; color: #d7e6ef; }
            QLabel { color: #9fd8d2; font-size: 14px; }
            QLineEdit, QPlainTextEdit, QListWidget { background:#101a2b; color:#e8f4ff;
                border:1px solid #1e3a5f; border-radius:8px; padding:6px; }
            QPushButton { background:#123047; color:#cfeaff; border:1px solid #2b6ea8;
                border-radius:8px; padding:8px 14px; font-weight:600; }
            QPushButton:hover { background:#1a4a6e; }
            QTabBar::tab { background:#101a2b; color:#9fd8d2; padding:8px 16px; }
            QTabBar::tab:selected { background:#123047; }
        """)

        central = QWidget()
        root = QHBoxLayout(central)
        self.setCentralWidget(central)

        # ---- левая колонка: реактор + статус + текст-команда ----
        left = QVBoxLayout()
        self.reactor = ReactorWidget()
        left.addWidget(self.reactor, 3)
        self.status_lbl = QLabel(STATE_TEXT["sleeping"], alignment=Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        left.addWidget(self.status_lbl)

        cmd_row = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Можно напечатать команду сюда (или говорите «Джарвис, …»)")
        send = QPushButton("Выполнить")
        send.clicked.connect(self._send_text_command)
        self.cmd_input.returnPressed.connect(self._send_text_command)
        cmd_row.addWidget(self.cmd_input)
        cmd_row.addWidget(send)
        left.addLayout(cmd_row)

        btns = QHBoxLayout()
        b_settings = QPushButton("⚙ Настройки")
        b_settings.clicked.connect(self._open_settings)
        b_stop = QPushButton("⏻ Спать")
        b_stop.clicked.connect(lambda: self.status_lbl.setText(STATE_TEXT["sleeping"]))
        btns.addWidget(b_settings)
        btns.addWidget(b_stop)
        left.addLayout(btns)

        left_col = QWidget(); left_col.setLayout(left); left_col.setMinimumWidth(320)
        root.addWidget(left_col, 1)

        # ---- правая колонка: вкладки Диалог / Браузер ----
        self.tabs = QTabWidget()
        # Диалог
        dlg_tab = QWidget(); dl = QVBoxLayout(dlg_tab)
        self.log = QListWidget()
        dl.addWidget(self.log)
        self.tabs.addTab(dlg_tab, "💬 Диалог")
        # Браузер
        if _HAS_WEB:
            self.browser = QWebEngineView()
            self.tabs.addTab(self.browser, "🌐 Браузер (Яндекс Музыка / VK)")
        else:
            w = QLabel("PyQt6-WebEngine не установлен — встроенный браузер недоступен.\n"
                       "pip install PyQt6-WebEngine")
            self.tabs.addTab(w, "🌐 Браузер недоступен")
        root.addWidget(self.tabs, 3)

        # ---- сигналы из потоков ассистента ----
        self.sig_state.connect(self._on_state)
        self.sig_heard.connect(lambda t: self._add_log("🎤 Вы", t))
        self.sig_reply.connect(lambda t: self._add_log("🤖 Джарвис", t))
        self.sig_open_url.connect(self._open_url)

        # ---- ассистент ----
        self.assistant = Assistant()
        self.assistant.on_state = self.sig_state.emit
        self.assistant.on_heard = self.sig_heard.emit
        self.assistant.on_reply = self.sig_reply.emit
        self.assistant.on_open_url = self.sig_open_url.emit
        if not text_only:
            self.assistant.start()
        else:
            self.assistant.awake = True  # печатные команды выполняются сразу

        cfg = self.assistant.cfg
        if _HAS_WEB:
            from PyQt6.QtCore import QUrl
            self.browser.setUrl(QUrl(cfg["browser"]["yandex_music_url"]))

    # ------------------------------------------------------------------
    def _on_state(self, s):
        self.reactor.set_state(s)
        self.status_lbl.setText(STATE_TEXT.get(s, s))

    def _add_log(self, who, text):
        item = QListWidgetItem(f"{who}: {text}")
        self.log.addItem(item)
        self.log.scrollToBottom()

    def _send_text_command(self):
        text = self.cmd_input.text().strip()
        if not text:
            return
        self.cmd_input.clear()
        self.sig_heard.emit(text)
        # кладём напрямую в очередь ассистента
        self.assistant.awake = True
        self.assistant._q.put(text)

    def _open_url(self, url):
        if _HAS_WEB:
            from PyQt6.QtCore import QUrl
            self.browser.setUrl(QUrl(url))
            self.tabs.setCurrentIndex(1)
        else:
            import webbrowser
            webbrowser.open(url)

    def _open_settings(self):
        dlg = SettingsDialog(self.assistant.cfg, self)
        dlg.exec()

    def closeEvent(self, e):
        self.assistant.stop()
        super().closeEvent(e)


def main():
    if "--list-voices" in sys.argv:
        Voice.list_voices()
        return
    text_only = "--text-only" in sys.argv
    app = QApplication(sys.argv)
    win = MainWindow(text_only=text_only)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
