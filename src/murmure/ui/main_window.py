from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from murmure.epub.reader import Chapter, load_epub
from murmure.text.chunker import chunk_text
from murmure.tts.cache import AudioCache
from murmure.tts.kokoro import KokoroEngine


class SynthesisWorker(QThread):
    ready = Signal(str)
    failed = Signal(str)

    def __init__(self, engine: KokoroEngine, cache: AudioCache, text: str, speed: float) -> None:
        super().__init__()
        self.engine = engine
        self.cache = cache
        self.text = text
        self.speed = speed

    def run(self) -> None:
        try:
            voice = "ff_siwis"
            path = self.cache.path_for(self.text, self.engine.name, voice, self.speed)
            if not path.exists():
                self.engine.synthesize(self.text, path, voice=voice, speed=self.speed)
            self.ready.emit(str(path))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Murmure")
        self.resize(1100, 720)

        self.chapters: list[Chapter] = []
        self.current_chunks: list[str] = []
        self.current_chunk_index = 0
        self.worker: SynthesisWorker | None = None
        self.cache = AudioCache()

        try:
            self.tts = KokoroEngine()
            tts_status = "Kokoro prêt"
        except Exception as exc:
            self.tts = None
            tts_status = f"TTS indisponible : {exc}"

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        self.open_button = QPushButton("Ouvrir un EPUB")
        self.play_button = QPushButton("Lire")
        self.pause_button = QPushButton("Pause")
        self.status = QLabel(tts_status)
        self.chapter_list = QListWidget()
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.speed_slider = QSlider()
        self.speed_slider.setOrientation(Qt.Horizontal)
        self.speed_slider.setMinimum(75)
        self.speed_slider.setMaximum(125)
        self.speed_slider.setValue(100)

        self.open_button.clicked.connect(self.open_epub)
        self.play_button.clicked.connect(self.start_reading)
        self.pause_button.clicked.connect(self.player.pause)
        self.chapter_list.currentRowChanged.connect(self.show_chapter)

        left = QVBoxLayout()
        left.addWidget(self.open_button)
        left.addWidget(QLabel("Chapitres"))
        left.addWidget(self.chapter_list)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(QLabel("Vitesse"))
        controls.addWidget(self.speed_slider)

        right = QVBoxLayout()
        right.addWidget(self.text_view)
        right.addLayout(controls)
        right.addWidget(self.status)

        layout = QHBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left)
        right_widget = QWidget()
        right_widget.setLayout(right)
        layout.addWidget(left_widget, 1)
        layout.addWidget(right_widget, 3)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_epub(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un livre EPUB", "", "EPUB (*.epub)")
        if not file_path:
            return

        try:
            self.chapters = load_epub(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur EPUB", str(exc))
            return

        self.chapter_list.clear()
        for chapter in self.chapters:
            self.chapter_list.addItem(chapter.title)

        if self.chapters:
            self.chapter_list.setCurrentRow(0)
        self.status.setText(f"{Path(file_path).name} — {len(self.chapters)} chapitre(s)")

    def show_chapter(self, index: int) -> None:
        if index < 0 or index >= len(self.chapters):
            return
        chapter = self.chapters[index]
        self.text_view.setPlainText(chapter.text)
        self.current_chunks = chunk_text(chapter.text)
        self.current_chunk_index = 0

    def start_reading(self) -> None:
        if not self.tts:
            QMessageBox.warning(self, "TTS indisponible", "Installez les modèles Kokoro dans models/ puis redémarrez Murmure.")
            return
        if not self.current_chunks:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.player.play()
            return
        self._synthesize_current_chunk()

    def _synthesize_current_chunk(self) -> None:
        if not self.tts or self.current_chunk_index >= len(self.current_chunks):
            self.status.setText("Chapitre terminé.")
            return

        text = self.current_chunks[self.current_chunk_index]
        speed = self.speed_slider.value() / 100
        self.status.setText(
            f"Synthèse {self.current_chunk_index + 1}/{len(self.current_chunks)}…"
        )

        self.worker = SynthesisWorker(self.tts, self.cache, text, speed)
        self.worker.ready.connect(self._play_file)
        self.worker.failed.connect(self._on_tts_error)
        self.worker.start()

    def _play_file(self, path: str) -> None:
        self.player.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
        self.player.play()
        self.status.setText(
            f"Lecture {self.current_chunk_index + 1}/{len(self.current_chunks)}"
        )

    def _on_tts_error(self, message: str) -> None:
        self.status.setText("Erreur de synthèse")
        QMessageBox.critical(self, "Erreur TTS", message)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.current_chunk_index += 1
            self._synthesize_current_chunk()


from PySide6.QtCore import Qt
