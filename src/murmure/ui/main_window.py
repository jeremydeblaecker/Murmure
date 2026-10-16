from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Signal, Qt
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
from murmure.progress import ProgressStore, ReadingProgress
from murmure.text.chunker import chunk_text
from murmure.tts.cache import AudioCache
from murmure.tts.kokoro import KokoroEngine


class SynthesisWorker(QThread):
    ready = Signal(int, int, str)
    failed = Signal(int, int, str)

    def __init__(self, engine: KokoroEngine, cache: AudioCache, text: str, speed: float, chunk_index: int, generation: int) -> None:
        super().__init__()
        self.engine = engine
        self.cache = cache
        self.text = text
        self.speed = speed
        self.chunk_index = chunk_index
        self.generation = generation

    def run(self) -> None:
        try:
            voice = "ff_siwis"
            path = self.cache.path_for(self.text, self.engine.name, voice, self.speed)
            if not path.exists():
                self.engine.synthesize(self.text, path, voice=voice, speed=self.speed)
            self.ready.emit(self.chunk_index, self.generation, str(path))
        except Exception as exc:
            self.failed.emit(self.chunk_index, self.generation, str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Murmure")
        self.resize(1100, 720)

        self.chapters: list[Chapter] = []
        self.current_chunks: list[str] = []
        self.current_chunk_index = 0
        self.generation = 0
        self.worker: SynthesisWorker | None = None
        self.prefetched_paths: dict[int, str] = {}
        self.pending_play_index: int | None = None
        self.cache = AudioCache()
        self.progress_store = ProgressStore()
        self.current_book_path: str | None = None

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

        self.current_book_path = file_path
        self.chapter_list.clear()
        for chapter in self.chapters:
            self.chapter_list.addItem(chapter.title)

        restored = self.progress_store.load(file_path)
        if restored:
            self.speed_slider.setValue(int(restored.speed * 100))
            chapter_index = min(max(restored.chapter_index, 0), max(len(self.chapters) - 1, 0))
            if self.chapters:
                self.chapter_list.setCurrentRow(chapter_index)
                self.current_chunk_index = min(max(restored.chunk_index, 0), max(len(self.current_chunks) - 1, 0))
            self.status.setText(
                f"{Path(file_path).name} — reprise chapitre {chapter_index + 1}, passage {self.current_chunk_index + 1}"
            )
        else:
            if self.chapters:
                self.chapter_list.setCurrentRow(0)
            self.status.setText(f"{Path(file_path).name} — {len(self.chapters)} chapitre(s)")

    def show_chapter(self, index: int) -> None:
        if index < 0 or index >= len(self.chapters):
            return

        self.player.stop()
        self.generation += 1
        self.prefetched_paths.clear()
        self.pending_play_index = None

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

        self._ensure_chunk(self.current_chunk_index, play_when_ready=True)

    def _cache_path_for(self, chunk_index: int) -> Path:
        text = self.current_chunks[chunk_index]
        speed = self.speed_slider.value() / 100
        return self.cache.path_for(text, "kokoro-onnx", "ff_siwis", speed)

    def _ensure_chunk(self, chunk_index: int, play_when_ready: bool) -> None:
        if not self.tts or chunk_index >= len(self.current_chunks):
            if play_when_ready:
                self.status.setText("Chapitre terminé.")
            return

        if chunk_index in self.prefetched_paths:
            if play_when_ready:
                self._play_chunk(chunk_index, self.prefetched_paths[chunk_index])
            return

        cache_path = self._cache_path_for(chunk_index)
        if cache_path.exists():
            self.prefetched_paths[chunk_index] = str(cache_path)
            if play_when_ready:
                self._play_chunk(chunk_index, str(cache_path))
            return

        if self.worker and self.worker.isRunning():
            if play_when_ready:
                self.pending_play_index = chunk_index
                self.status.setText(f"Préparation {chunk_index + 1}/{len(self.current_chunks)}…")
            return

        self._start_synthesis(chunk_index, play_when_ready)

    def _start_synthesis(self, chunk_index: int, play_when_ready: bool) -> None:
        if not self.tts:
            return

        text = self.current_chunks[chunk_index]
        speed = self.speed_slider.value() / 100
        if play_when_ready:
            self.pending_play_index = chunk_index
            self.status.setText(f"Synthèse {chunk_index + 1}/{len(self.current_chunks)}…")
        else:
            self.status.setText(f"Lecture {self.current_chunk_index + 1}/{len(self.current_chunks)} · préparation suivante…")

        self.worker = SynthesisWorker(self.tts, self.cache, text, speed, chunk_index, self.generation)
        self.worker.ready.connect(self._on_synthesis_ready)
        self.worker.failed.connect(self._on_tts_error)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_synthesis_ready(self, chunk_index: int, generation: int, path: str) -> None:
        if generation != self.generation:
            return

        self.prefetched_paths[chunk_index] = path
        if self.pending_play_index == chunk_index:
            self.pending_play_index = None
            self._play_chunk(chunk_index, path)

    def _on_worker_finished(self) -> None:
        self.worker = None

        if self.pending_play_index is not None:
            pending = self.pending_play_index
            self._ensure_chunk(pending, play_when_ready=True)
            return

        next_index = self.current_chunk_index + 1
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and next_index < len(self.current_chunks):
            self._ensure_chunk(next_index, play_when_ready=False)

    def _play_chunk(self, chunk_index: int, path: str) -> None:
        if chunk_index != self.current_chunk_index:
            return

        self.player.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
        self.player.play()
        self.status.setText(f"Lecture {chunk_index + 1}/{len(self.current_chunks)}")
        self._save_progress()

        next_index = chunk_index + 1
        if next_index < len(self.current_chunks):
            self._ensure_chunk(next_index, play_when_ready=False)

    def _on_tts_error(self, chunk_index: int, generation: int, message: str) -> None:
        if generation != self.generation:
            return
        if self.pending_play_index == chunk_index:
            self.pending_play_index = None
        self.status.setText("Erreur de synthèse")
        QMessageBox.critical(self, "Erreur TTS", message)


    def _save_progress(self) -> None:
        if not self.current_book_path:
            return

        chapter_index = self.chapter_list.currentRow()
        if chapter_index < 0:
            return

        progress = ReadingProgress(
            book_id=self.progress_store.book_id(self.current_book_path),
            path=self.current_book_path,
            chapter_index=chapter_index,
            chunk_index=self.current_chunk_index,
            speed=self.speed_slider.value() / 100,
        )
        self.progress_store.save(progress)

    def closeEvent(self, event) -> None:
        self._save_progress()
        super().closeEvent(event)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return

        self.current_chunk_index += 1
        self._save_progress()
        self._ensure_chunk(self.current_chunk_index, play_when_ready=True)
