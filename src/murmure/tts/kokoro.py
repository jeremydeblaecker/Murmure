from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro
from misaki import espeak
from misaki.espeak import EspeakG2P

from .base import TtsEngine


class KokoroEngine(TtsEngine):
    name = "kokoro-onnx"

    def __init__(self, model_dir: Path | None = None) -> None:
        model_dir = model_dir or Path("models")
        model_path = model_dir / "kokoro-v1.0.onnx"
        voices_path = model_dir / "voices-v1.0.bin"

        if not model_path.exists() or not voices_path.exists():
            raise FileNotFoundError(
                "Modèles Kokoro introuvables. Placez kokoro-v1.0.onnx et voices-v1.0.bin dans le dossier models/."
            )

        self.kokoro = Kokoro(str(model_path), str(voices_path))
        fallback = espeak.EspeakFallback(british=False)
        self.g2p = EspeakG2P(language="fr-fr", fallback=fallback)

    def synthesize(self, text: str, output_path: Path, voice: str = "ff_siwis", speed: float = 1.0) -> Path:
        phonemes, _ = self.g2p(text)
        samples, sample_rate = self.kokoro.create(phonemes, voice=voice, speed=speed, is_phonemes=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), samples, sample_rate, subtype="PCM_16")
        return output_path

    def close(self) -> None:
        voices = getattr(self.kokoro, "voices", None)
        if voices and hasattr(voices, "close"):
            voices.close()
