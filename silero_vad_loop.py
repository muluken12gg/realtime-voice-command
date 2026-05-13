"""Silero VAD + microphone capture; emits one utterance at a time to whisper-cli."""

from __future__ import annotations

import os
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
import sounddevice as sd

SR = 16000
WIN = 512


def load_silero_model():
    import torch

    model, _utils = torch.hub.load(
        "snakers4/silero-vad",
        "silero_vad",
        force_reload=False,
        onnx=False,
        trust_repo=True,
    )
    model.eval()
    return model


def _speech_prob(model, chunk_f32: np.ndarray) -> float:
    import torch

    x = torch.from_numpy(chunk_f32.astype(np.float32, copy=False))
    if x.ndim == 1:
        x = x.unsqueeze(0)
    with torch.no_grad():
        return float(model(x, SR).item())


def _write_wav_int16(path: Path, samples_f32: np.ndarray) -> None:
    samples_f32 = np.clip(samples_f32, -1.0, 1.0)
    pcm = (samples_f32 * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def transcribe_utterance(
    whisper_cli: Path,
    whisper_model: Path,
    cwd: Path,
    samples_f32: np.ndarray,
    threads: int,
) -> str:
    if samples_f32.size < int(0.12 * SR):
        return ""
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wav_path = Path(tmp)
    try:
        _write_wav_int16(wav_path, samples_f32)
        cmd = [
            str(whisper_cli),
            "--model",
            str(whisper_model.resolve()),
            "-f",
            str(wav_path),
            "-l",
            "en",
            "-nt",
            "-np",
            "--no-fallback",
            "-sns",
            "-t",
            str(threads),
        ]
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=120,
        )
        if r.returncode != 0:
            return ""
        return (r.stdout or "").strip()
    finally:
        try:
            wav_path.unlink(missing_ok=True)
        except OSError:
            pass


def iter_vad_transcripts(
    root: Path,
    whisper_cli: Path,
    whisper_model: Path,
    device_index: Optional[int] = None,
    speech_threshold: float = 0.55,
    min_speech_ms: float = 220.0,
    end_silence_ms: float = 520.0,
    max_utterance_s: float = 25.0,
    threads: Optional[int] = None,
) -> Iterator[str]:
    """
    Block on microphone; when a speech segment ends, run whisper-cli once and yield text.
    """
    if threads is None:
        threads = max(1, min(8, (os.cpu_count() or 4)))
    if not whisper_cli.is_file():
        raise SystemExit(f"Missing {whisper_cli}")
    if not whisper_model.is_file():
        raise SystemExit(f"Missing model {whisper_model}")

    print("Loading Silero VAD…")
    model = load_silero_model()

    min_speech_samples = int(SR * (min_speech_ms / 1000.0))
    end_silence_samples = int(SR * (end_silence_ms / 1000.0))
    max_samples = int(SR * max_utterance_s)

    dev = None if device_index is None or device_index < 0 else device_index

    buf: list[np.ndarray] = []
    in_speech = False
    trail_silence = 0

    print("🎤Silero VAD listening (Ctrl+C to stop)…")

    while True:
        block = sd.rec(
            WIN,
            samplerate=SR,
            channels=1,
            dtype="float32",
            device=dev,
            blocking=True,
        )
        chunk = np.squeeze(block, axis=-1)
        if chunk.shape[0] != WIN:
            continue

        p = _speech_prob(model, chunk)
        is_speech = p >= speech_threshold

        if is_speech:
            in_speech = True
            buf.append(chunk.copy())
            trail_silence = 0
            total = sum(len(b) for b in buf)
            if total >= max_samples:
                audio = np.concatenate(buf, axis=0)
                buf.clear()
                in_speech = False
                trail_silence = 0
                text = transcribe_utterance(
                    whisper_cli, whisper_model, root, audio, threads
                )
                if text:
                    yield text
            continue

        if in_speech:
            buf.append(chunk.copy())
            trail_silence += WIN
            if trail_silence >= end_silence_samples:
                trim = min(trail_silence, sum(len(b) for b in buf))
                audio = np.concatenate(buf, axis=0)
                if trim <= audio.shape[0]:
                    audio = audio[: audio.shape[0] - trim]
                buf.clear()
                in_speech = False
                trail_silence = 0
                if audio.shape[0] >= min_speech_samples:
                    text = transcribe_utterance(
                        whisper_cli, whisper_model, root, audio, threads
                    )
                    if text:
                        yield text
