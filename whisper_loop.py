"""Microphone capture + Whisper speech recognition; yields finalized utterance text."""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
import sounddevice as sd

SR = 16000
BLOCK_SAMPLES = 4000

SILENCE_THRESHOLD = 500
SILENCE_DURATION_SEC = 0.8
MIN_SPEECH_SEC = 0.3
MAX_SEGMENT_SEC = 15.0


def resolve_whisper_model(root: Path) -> str:
    raw = os.environ.get("WHISPER_MODEL", "").strip()
    if raw:
        return raw

    return "base"


def iter_whisper_transcripts(
    root: Path,
    model_name: Optional[str] = None,
    device_index: Optional[int] = None,
    sample_rate: int = SR,
    block_samples: int = BLOCK_SAMPLES,
) -> Iterator[dict]:
    """
    Block on the microphone; accumulate audio until silence is detected,
    then transcribe the segment with Whisper and yield the result.
    """
    import queue
    import whisper

    resolved = model_name or resolve_whisper_model(root)
    print(f"Loading Whisper model: {resolved}")
    model = whisper.load_model(resolved)

    dev = None if device_index is None or device_index < 0 else device_index
    audio_queue: queue.Queue = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status)
        audio_queue.put(bytes(indata))

    speech_buffer: list[np.ndarray] = []
    silence_counter = 0
    is_speaking = False

    frames_per_sec = sample_rate / block_samples
    silence_limit = int(SILENCE_DURATION_SEC * frames_per_sec)
    min_speech_frames = int(MIN_SPEECH_SEC * frames_per_sec)
    max_speech_frames = int(MAX_SEGMENT_SEC * frames_per_sec)

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
            audio_np = np.frombuffer(data, dtype=np.int16)
            energy = int(np.abs(audio_np).mean())

            if energy > SILENCE_THRESHOLD:
                is_speaking = True
                silence_counter = 0
                speech_buffer.append(audio_np)
            else:
                if is_speaking:
                    silence_counter += 1
                    speech_buffer.append(audio_np)

                total_frames = len(speech_buffer)
                if (
                    is_speaking
                    and silence_counter >= silence_limit
                    and total_frames >= min_speech_frames
                ) or (
                    is_speaking
                    and total_frames >= max_speech_frames
                ):
                    audio_data = np.concatenate(speech_buffer)

                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp_path = tmp.name
                        with wave.open(tmp_path, "wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(sample_rate)
                            wf.writeframes(audio_data.tobytes())

                    try:
                        result = model.transcribe(
                            tmp_path,
                            language="en",
                            fp16=False,
                        )
                        text = (result.get("text") or "").strip()
                        if text:
                            yield {"type": "final", "text": text}
                    finally:
                        os.unlink(tmp_path)

                    speech_buffer.clear()
                    silence_counter = 0
                    is_speaking = False
