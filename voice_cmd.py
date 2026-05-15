import os
import time
from dataclasses import dataclass
from pathlib import Path

import commands
from vosk_loop import iter_vosk_transcripts, resolve_vosk_model

ROOT = Path(__file__).resolve().parent

DEVICE_INDEX = int(os.environ.get("VOSK_DEVICE", os.environ.get("WHISPER_DEVICE", "-1")))
POST_WAKE_CMD_SEC = float(
    os.environ.get("VOSK_POST_WAKE_SEC", os.environ.get("WHISPER_POST_WAKE_SEC", "1.25"))
)


@dataclass
class ChatState:
    awake: bool = False
    post_wake_cmd_until: float = 0.0


def is_noise_transcript(line: str) -> bool:
    u = line.upper()
    if "BLANK_AUDIO" in u:
        return True
    low = line.lower()
    if "blank" in low and "audio" in low:
        return True
    for token in ("[NOISE]", "[MUSIC]", "[APPLAUSE]", "[SILENCE]", "[SONG]"):
        if token in u:
            return True
    return False


def print_input_devices() -> None:
    try:
        import sounddevice as sd
    except ImportError:
        print("ℹ️ pip install sounddevice — to list microphone indices here.")
        return
    try:
        default_in = sd.default.device[0]
    except Exception:
        default_in = None
    print("🎧Input devices (set VOSK_DEVICE=<index> if the mic is silent):")
    for i, d in enumerate(sd.query_devices()):
        if int(d.get("max_input_channels") or 0) <= 0:
            continue
        tag = "default" if default_in is not None and i == default_in else ""
        extra = f" — {tag}" if tag else ""
        print(f"  [{i}] {d.get('name', '?')}{extra}")
    print(f"   VOSK_DEVICE is currently {DEVICE_INDEX}")


def process_transcript_line(raw_line: str, state: ChatState, wake_word: str) -> None:
    text = raw_line.strip()
    if not text:
        return
    print("🗣️", text)
    normalized = commands.normalize(text)

    if not normalized:
        return

    if normalized in commands.ignored_phrases:
        return

    if (wake_word in normalized or "im peter" in normalized) and not state.awake:
        state.awake = True
        state.post_wake_cmd_until = time.monotonic() + POST_WAKE_CMD_SEC
        commands.speak("Yes?")
        print("✅Wake word detected")
        return

    if state.awake:
        if time.monotonic() < state.post_wake_cmd_until:
            return
        commands.handle_command(normalized)
        state.awake = False

    if "hello" in normalized:
        commands.speak("What's up Muluken?")

    if "yeah no" in normalized:
        commands.speak("Yerosat isa doormii keetii sanamoo")

    if "thank you" in normalized:
        commands.speak("you're welcome")
        print("you're welcome")


def run_vosk_loop(state: ChatState, wake_word: str, model_path: Path) -> None:
    dev = DEVICE_INDEX if DEVICE_INDEX >= 0 else None
    for raw_line in iter_vosk_transcripts(
        ROOT,
        model_path=model_path,
        device_index=dev,
    ):
        if is_noise_transcript(raw_line):
            continue
        process_transcript_line(raw_line, state, wake_word)


def main() -> None:
    model_path = resolve_vosk_model(ROOT)
    print(f"🎯Vosk model: {model_path.name} (set VOSK_MODEL to override)")
    if DEVICE_INDEX < 0:
        print("🎧Capture device is default (-1). Set VOSK_DEVICE if you get silence.")
    print_input_devices()

    state = ChatState()
    wake_word = "computer"

    print("🎤Listening... Speak now (Ctrl + C to stop)")

    try:
        run_vosk_loop(state, wake_word, model_path)
    except KeyboardInterrupt:
        print("\nStopping…")


if __name__ == "__main__":
    main()
