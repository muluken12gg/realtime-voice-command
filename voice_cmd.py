import os
import subprocess
import time
from pathlib import Path

import commands

ROOT = Path(__file__).resolve().parent
STREAM_EXE = ROOT / "Release" / "whisper-stream.exe"
MODELS_DIR = ROOT / "Release" / "models"

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

# After this many seconds blocked in readline(), switch to a faster model if one exists.
# whisper-stream emits a newline every n_new_line decode passes (see stream.cpp). With
# step=1000 and length=2000, n_new_line is 1, so Python readline tracks each window closely.
SLOW_READLINE_SEC = float(os.environ.get("WHISPER_SLOW_READLINE_SEC", "6.0"))
# Ignore slow spikes during model warm-up / first transcripts.
WARMUP_LINE_READS = int(os.environ.get("WHISPER_WARMUP_READS", "6"))
DEVICE_INDEX = int(os.environ.get("WHISPER_DEVICE", "-1"))


def tier_for_model_path(path: Path) -> int:
    name = path.name.lower()
    for fname, tier in MODEL_CANDIDATES:
        if name == fname.lower():
            return tier
    return 99


def scan_models_by_tier() -> dict[int, Path]:
    """Map tier -> preferred model path (fastest filename wins within tier)."""
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
        "1000",
        "--length",
        "2000",
        "--keep",
        "200",
        "--threads",
        str(threads),
    ]


def start_stream(model_path: Path) -> subprocess.Popen[str]:
    if not STREAM_EXE.is_file():
        raise SystemExit(f"Missing {STREAM_EXE}")
    cmd = build_stream_command(model_path)
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        cwd=str(ROOT),
    )


def main() -> None:
    tier_map = scan_models_by_tier()
    model_path, current_tier = pick_fastest_model(tier_map)
    print(
        f"🎯Whisper model: {model_path.name} (tier {current_tier}; lower is faster). "
        f"Set WHISPER_MODEL to override."
    )

    proc = start_stream(model_path)
    wake_word = "computer"
    awake = False
    warmup_reads = 0

    print("🎤Listening... Speak now (Ctrl + C to stop)")

    try:
        while True:
            t0 = time.perf_counter()
            line = proc.stdout.readline()
            read_dt = time.perf_counter() - t0

            if line == "" and proc.poll() is not None:
                break

            warmup_reads += 1
            nf = next_faster_tier(current_tier, tier_map)
            if (
                warmup_reads > WARMUP_LINE_READS
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
                warmup_reads = 0

            text = line.strip()
            if text:
                print("🗣️", text)
                normalized = commands.normalize(text)

                if not normalized:
                    continue

                if normalized in commands.ignored_phrases:
                    continue

                if (wake_word in normalized or "im peter" in normalized) and not awake:
                    awake = True
                    commands.speak("Yes?")
                    print("✅Wake word detected")
                    continue

                if awake:
                    commands.handle_command(normalized)
                    awake = False

                if "hello" in normalized:
                    commands.speak("What's up Muluken?")

                if "yeah no" in normalized:
                    commands.speak("Yerosat isa doormii keetii sanamoo")

                if "thank you" in normalized:
                    commands.speak("you're welcome")
                    print("you're welcome")
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
