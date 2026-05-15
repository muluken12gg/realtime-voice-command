import sounddevice as sd
import numpy as np

print("Testing microphone device 1 (Microphone Array)...")
print("Please speak into your microphone now...")
print()

try:
    recording = sd.rec(int(16000 * 3), samplerate=16000, channels=1, dtype='int16', device=1, blocking=True)
    max_vol = np.max(np.abs(recording))
    avg_vol = np.mean(np.abs(recording))
    print(f"Max volume: {max_vol}")
    print(f"Average volume: {avg_vol}")
    if max_vol > 100:
        print("✓ Microphone is working!")
    else:
        print("✗ Microphone is silent - check Windows settings")
except Exception as e:
    print(f"✗ Error: {e}")
