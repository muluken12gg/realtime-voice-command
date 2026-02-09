import queue
import sys
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import json
import webbrowser

def handle_command(text):
    if "open browser" in text:
        webbrowser.open("https://google.com")
        print("🌐Opening browser")

    elif "open youtube" in text:
        webbrowser.open("https://youtube.com")
        print("⏯️Opening YouTube")
    elif "shut down" in text:
        print("⚠️Shutdown command blocked(safety)")
    else:
        print("❓Unknown command")

MODEL_PATH = "vosk-model-small-en-us-0.15"
DEVICE_INDEX = 5

device_info = sd.query_devices(DEVICE_INDEX, 'input')
SAMPLE_RATE = int(device_info['default_samplerate'])

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    pcm16 = (indata * 32767).astype('int16')
    q.put(pcm16.tobytes())

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

wake_word = "computer"
awake = False

with sd.InputStream(
    samplerate = SAMPLE_RATE,
    blocksize = 4000,
    dtype = "float32",
    channels = 1,
    callback = callback
):
    print(f"🎤Listening in device [DEVICE_INDEX] at [SAMPLE_RATE] hz ... Speak now(Ctrl + C to stop)")
    while True:
        data = q.get()

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")

            if not text:
                continue

            print("🗣️", text)
            if wake_word in text and not awake:
                awake = True
                print("✅Wake word detectd")
                continue

            if awake:
                handle_command(text)
                awake = False

        else:
            partial = json.loads(recognizer.PartialResult())
            if partial.get("partial"):
                print("...", partial["partil"])