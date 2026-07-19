import os
import time
from dataclasses import dataclass
from pathlib import Path

import commands

ROOT = Path(__file__).resolve().parent

DEVICE_INDEX = int(os.environ.get("WHISPER_DEVICE", "1"))
POST_WAKE_CMD_SEC = float(
    os.environ.get("WHISPER_POST_WAKE_SEC", "1.25")
)


@dataclass
class ChatState:
    awake: bool = False
    post_wake_cmd_until: float = 0.0

def process_transcript_line(raw_line: str, state: ChatState, wake_word: str, use_wake_word: bool = True) -> None:
    if commands.speaking:
        return
    text = raw_line.strip()
    if not text:
        return

    print(text)
    normalized = commands.normalize(text)

    if not normalized:
        return

    if normalized in commands.ignored_phrases:
        return

    if use_wake_word and normalized.startswith(wake_word) and not state.awake:
        cmd = normalized[len(wake_word):].strip()

        if cmd:
            commands.handle_command(cmd)
            return

        state.awake = True
        state.post_wake_cmd_until = time.monotonic() + POST_WAKE_CMD_SEC
        commands.speak("Yes?")
        return

    if use_wake_word and state.awake:
        if time.monotonic() < state.post_wake_cmd_until:
            return
        commands.handle_command(normalized)
        state.awake = False

    if not use_wake_word:
        commands.handle_command(normalized)

    if "hello" in normalized:
        commands.speak("What's up Muluken?")

    if "yeah no" in normalized:
        commands.speak("Yerosat isa doormii keetii sanamoo")

    if "thank you" in normalized:
        commands.speak("you're welcome")


def run_whisper_loop(state: ChatState, wake_word: str, model_name: str) -> None:
    from whisper_loop import iter_whisper_transcripts

    dev = DEVICE_INDEX if DEVICE_INDEX >= 0 else None
    for event in iter_whisper_transcripts(
        ROOT,
        model_name=model_name,
        device_index=dev,
    ):
        text = event["text"]

        print(f"📝 {text}")

        process_transcript_line(text, state, wake_word)


def run_chat_loop(state: ChatState) -> None:
    while True:
        try:
            text = input("💬> ")
        except (EOFError, KeyboardInterrupt):
            print("\nStopping…")
            break
        if text.strip().lower() in ("quit", "exit"):
            break
        process_transcript_line(text, state, wake_word="", use_wake_word=False)


def choose_mode() -> str:
    while True:
        choice = input("Choose mode (voice/chat): ").strip().lower()
        if choice in ("voice", "chat"):
            return choice
        print("Please enter 'voice' or 'chat'.")


def main() -> None:
    mode = choose_mode()
    state = ChatState()
    wake_word = "nero"

    if mode == "voice":
        from whisper_loop import resolve_whisper_model

        model_name = resolve_whisper_model(ROOT)
        try:
            run_whisper_loop(state, wake_word, model_name)
        except KeyboardInterrupt:
            print("\nStopping…")
    else:
        try:
            run_chat_loop(state)
        except KeyboardInterrupt:
            print("\nStopping…")


if __name__ == "__main__":
    main()