"""Microphone capture + Vosk speech recognition; yields finalized utterance text."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator, Optional

import sounddevice as sd
from vosk import KaldiRecognizer, Model, SetLogLevel

SetLogLevel(-1)

SR = 16000
BLOCK_SAMPLES = 4000

DEFAULT_MODEL_NAMES = (
    "vosk-model-small-en-us-0.15",
    "vosk-model-en-us-0.22",
    "vosk-model-en-us-0.21",
)


def _looks_like_vosk_model(path: Path) -> bool:
    return path.is_dir() and any((path / name).exists() for name in ("am", "graph", "conf"))


def resolve_vosk_model(root: Path) -> Path:
    raw = os.environ.get("VOSK_MODEL", "").strip()
    if raw:
        candidate = Path(raw)
        if not candidate.is_dir():
            candidate = root / raw
        if _looks_like_vosk_model(candidate):
            return candidate
        raise SystemExit(f"VOSK_MODEL not found or invalid: {raw!r}")

    models_dir = root / "models"
    if models_dir.is_dir():
        for name in DEFAULT_MODEL_NAMES:
            candidate = models_dir / name
            if _looks_like_vosk_model(candidate):
                return candidate
        for child in sorted(models_dir.iterdir()):
            if _looks_like_vosk_model(child):
                return child

    for name in DEFAULT_MODEL_NAMES:
        candidate = root / name
        if _looks_like_vosk_model(candidate):
            return candidate

    raise SystemExit(
        f"No Vosk model found under {models_dir}/. "
        "Download an English model (e.g. vosk-model-small-en-us-0.15) "
        "or set VOSK_MODEL to the model directory."
    )


def iter_vosk_transcripts(
    root: Path,
    model_path: Optional[Path] = None,
    device_index: Optional[int] = None,
    sample_rate: int = SR,
    block_samples: int = BLOCK_SAMPLES,
) -> Iterator[str]:
    """
    Block on the microphone; yield non-empty transcript text when Vosk
    finalizes an utterance.
    """

    import queue

    resolved = model_path or resolve_vosk_model(root)
    if not _looks_like_vosk_model(resolved):
        raise SystemExit(f"Invalid Vosk model directory: {resolved}")

    model = Model(str(resolved.resolve()))
    recognizer = KaldiRecognizer(model, sample_rate)
    recognizer.SetWords(False)

    dev = None if device_index is None or device_index < 0 else device_index

    audio_queue = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        """
        Runs automatically whenever microphone audio arrives.
        """

        if status:
            print(status)

        audio_queue.put(bytes(indata))

    with sd.InputStream(
        samplerate=sample_rate,
        blocksize=block_samples,
        device=dev,
        channels=1,
        dtype="int16",
        callback=audio_callback,
    ):
        while True:
            data = audio_queue.get()

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = (result.get("text") or "").strip()
                if text:
                    yield {
                        "type" : "final",
                        "text" : text,
                    }
            else:
                partial = json.loads(recognizer.PartialResult())
                partial_text = (partial.get("partial") or "").strip()
                if partial_text:
                    yield {
                        "type" : "partial",
                        "text" : partial_text,
                    }