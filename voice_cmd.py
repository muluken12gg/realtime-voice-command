import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import commands

ROOT = Path(__file__).resolve().parent
STREAM_EXE = ROOT / "Release" / "whisper-stream.exe"
WHISPER_CLI = ROOT / "Release" / "whisper-cli.exe"
MODELS_DIR = ROOT / "Release" / "models"

USE_SILERO_VAD = os.environ.get("USE_SILERO_VAD", "1") != "0"

# Smaller tier number = faster inference. First filename match wins per tier.
MODEL_CANDIDATES = (
    ("ggml-tiny.en.bin", 0),
    ("ggml-tiny.bin", 0),
    ("ggml-base.en.bin", 1),
    ("ggml-base.bin", 1),
    ("ggml-small.en.bin", 2),
    ("ggml-small.bin", 2),
    ("ggml-medium.en.bin", 3),
    ("ggml-medium.bin", 3),
    ("ggml-large-v1.bin", 4),
    ("ggml-large-v2.bin", 4),
    ("ggml-large-v3.bin", 4),
    ("ggml-large-v3-turbo.bin", 4),
)

SLOW_READLINE_SEC = float(os.environ.get("WHISPER_SLOW_READLINE_SEC", "6.0"))
WARMUP_LINE_READS = int(os.environ.get("WHISPER_WARMUP_READS", "6"))
DEVICE_INDEX = int(os.environ.get("WHISPER_DEVICE", "-1"))
POST_WAKE_CMD_SEC = float(os.environ.get("WHISPER_POST_WAKE_SEC", "1.25"))
WHISPER_STEP_MS = int(os.environ.get("WHISPER_STEP_MS", "3000"))
WHISPER_LENGTH_MS = int(os.environ.get("WHISPER_LENGTH_MS", "10000"))


@dataclass
class ChatState:
    awake: bool = False
    post_wake_cmd_until: float = 0.0
    warmup_reads: int = 0


def tier_for_model_path(path: Path) -> int:
    name = path.name.lower()
    for fname, tier in MODEL_CANDIDATES:
        if name == fname.lower():
            return tier
    return 99


def scan_models_by_tier() -> dict[int, Path]:
    if not MODELS_DIR.is_dir():
        return {}
    found: dict[int, Path] = {}
    for fname, tier in MODEL_CANDIDATES:
        candidate = MODELS_DIR / fname
        if candidate.is_file():
            found.setdefault(tier, candidate)
    return found


def pick_model_from_env(tier_map: dict[int, Path]) -> tuple[Path, int] | None:
    raw = os.environ.get("WHISPER_MODEL", "").strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.is_file():
        p = MODELS_DIR / raw
    if not p.is_file():
        print(f"⚠️WHISPER_MODEL not found: {raw!r}, using auto selection.")
        return None
    return p, tier_for_model_path(p)


def pick_fastest_model(tier_map: dict[int, Path]) -> tuple[Path, int]:
    forced = pick_model_from_env(tier_map)
    if forced is not None:
        return forced
    if not tier_map:
        raise SystemExit(
            f"No Whisper models found in {MODELS_DIR}. "
            "Add e.g. ggml-base.en.bin or ggml-tiny.en.bin for low latency."
        )
    best_tier = min(tier_map)
    return tier_map[best_tier], best_tier


def next_faster_tier(current_tier: int, tier_map: dict[int, Path]) -> int | None:
    for t in range(current_tier - 1, -1, -1):
        if t in tier_map:
            return t
    return None


def build_stream_command(model_path: Path) -> list[str]:
    threads = max(1, min(8, (os.cpu_count() or 4)))
    mp = str(model_path.resolve())
    return [
        str(STREAM_EXE),
        "--model",
        mp,
        "--capture",
        str(DEVICE_INDEX),
        "--language",
        "en",
        "--step",
        str(WHISPER_STEP_MS),
        "--length",
        str(WHISPER_LENGTH_MS),
        "--keep",
        "200",
        "--threads",
        str(threads),
        "--no-fallback",
    ]


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
    print("🎧Input devices (set WHISPER_DEVICE=<index> if you get silence or [BLANK_AUDIO]):")
    for i, d in enumerate(sd.query_devices()):
        if int(d.get("max_input_channels") or 0) <= 0:
            continue
        tag = "default" if default_in is not None and i == default_in else ""
        extra = f" — {tag}" if tag else ""
        print(f"  [{i}] {d.get('name', '?')}{extra}")
    print(f"   WHISPER_DEVICE is currently {DEVICE_INDEX}")


def start_stderr_watcher(proc: subprocess.Popen[str]) -> None:
    err = proc.stderr
    if err is None:
        return

    def run() -> None:
        for line in iter(err.readline, ""):
            if not line:
                break
            low = line.lower()
            if "warning" in low or "cannot process" in low or "error" in low:
                print("⚠️whisper-stream:", line.rstrip())

    threading.Thread(target=run, daemon=True).start()


def start_stream(model_path: Path) -> subprocess.Popen[str]:
    if not STREAM_EXE.is_file():
        raise SystemExit(f"Missing {STREAM_EXE}")
    cmd = build_stream_command(model_path)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(ROOT),
    )
    start_stderr_watcher(proc)
    return proc


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


def run_silero_vad_loop(
    model_path: Path,
    state: ChatState,
    wake_word: str,
) -> None:
    from silero_vad_loop import iter_vad_transcripts

    speech_th = float(os.environ.get("SILERO_SPEECH_TH", "0.55"))
    min_sp = float(os.environ.get("SILERO_MIN_SPEECH_MS", "220"))
    end_sil = float(os.environ.get("SILERO_END_SILENCE_MS", "520"))

    for block in iter_vad_transcripts(
        ROOT,
        WHISPER_CLI,
        model_path,
        device_index=DEVICE_INDEX if DEVICE_INDEX >= 0 else None,
        speech_threshold=speech_th,
        min_speech_ms=min_sp,
        end_silence_ms=end_sil,
    ):
        for raw_line in block.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            if is_noise_transcript(raw_line):
                continue
            process_transcript_line(raw_line, state, wake_word)


def run_whisper_stream_loop(
    model_path: Path,
    current_tier: int,
    tier_map: dict[int, Path],
    state: ChatState,
    wake_word: str,
) -> None:
    proc = start_stream(model_path)
    try:
        while True:
            t0 = time.perf_counter()
            line = proc.stdout.readline()
            read_dt = time.perf_counter() - t0

            if line == "" and proc.poll() is not None:
                break

            if is_noise_transcript(line):
                continue

            state.warmup_reads += 1
            nf = next_faster_tier(current_tier, tier_map)
            if (
                state.warmup_reads > WARMUP_LINE_READS
                and read_dt >= SLOW_READLINE_SEC
                and nf is not None
            ):
                print(
                    f"⏱️Transcription stalled {read_dt:.1f}s; switching to "
                    f"{tier_map[nf].name}..."
                )
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                current_tier = nf
                model_path = tier_map[current_tier]
                proc = start_stream(model_path)
                state.warmup_reads = 0

            process_transcript_line(line, state, wake_word)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> None:
    tier_map = scan_models_by_tier()
    model_path, current_tier = pick_fastest_model(tier_map)
    print(
        f"🎯Whisper model: {model_path.name} (tier {current_tier}; lower is faster). "
        f"Set WHISPER_MODEL to override."
    )
    mode = "Silero VAD + whisper-cli" if USE_SILERO_VAD else "whisper-stream"
    print(f"🔊Mode: {mode} (set USE_SILERO_VAD=0 for whisper-stream only)")
    if DEVICE_INDEX < 0:
        print(
            "🎧Capture device is default (-1). If you only see [BLANK_AUDIO], "
            "set WHISPER_DEVICE to your mic index from the list below."
        )
    print_input_devices()

    state = ChatState()
    wake_word = "computer"

    print("🎤Listening... Speak now (Ctrl + C to stop)")

    try:
        if USE_SILERO_VAD:
            if not WHISPER_CLI.is_file():
                raise SystemExit(f"Missing {WHISPER_CLI} (required for Silero VAD mode)")
            run_silero_vad_loop(model_path, state, wake_word)
        else:
            run_whisper_stream_loop(model_path, current_tier, tier_map, state, wake_word)
    except KeyboardInterrupt:
        print("\nStopping…")


if __name__ == "__main__":
    main()
