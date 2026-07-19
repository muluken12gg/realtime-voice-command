import os
import time
from dataclasses import dataclass
from pathlib import Path

import commands
from whisper_loop import iter_whisper_transcripts, resolve_whisper_model

ROOT = Path(__file__).resolve().parent

DEVICE_INDEX = int(os.environ.get("WHISPER_DEVICE", "1"))
POST_WAKE_CMD_SEC = float(
    os.environ.get("WHISPER_POST_WAKE_SEC", "1.25")
)


@dataclass
class ChatState:
    awake: bool = False
    post_wake_cmd_until: float = 0.0

def process_transcript_line(raw_line: str, state: ChatState, wake_word: str) -> None:
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

    if normalized.startswith(wake_word) and not state.awake:
        cmd = normalized[len(wake_word):].strip()

        # Example:
        # "computer open vscode"
        # immediately executes the command
        if cmd:
            commands.handle_command(cmd)
            return

        # Example:
        # user only says "computer"
        state.awake = True
        state.post_wake_cmd_until = time.monotonic() + POST_WAKE_CMD_SEC
        commands.speak("Yes?")
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


def run_whisper_loop(state: ChatState, wake_word: str, model_name: str) -> None:
    dev = DEVICE_INDEX if DEVICE_INDEX >= 0 else None
    for event in iter_whisper_transcripts(
        ROOT,
        model_name=model_name,
        device_index=dev,
    ):
        text = event["text"]

        print(f"📝 {text}")

        process_transcript_line(text, state, wake_word)


def choose_mode() -> str:
    while True:
        choice = input("Choose mode (voice/chat): ").strip().lower()
        if choice in ("voice", "chat"):
            return choice
        print("Please enter 'voice' or 'chat'.")


def main() -> None:
    mode = choose_mode()
    model_name = resolve_whisper_model(ROOT)
    state = ChatState()
    wake_word = "nero"

    if mode == "voice":
        try:
            run_whisper_loop(state, wake_word, model_name)
        except KeyboardInterrupt:
            print("\nStopping…")
    else:
        print("Chat mode not yet implemented.")


if __name__ == "__main__":
    main()