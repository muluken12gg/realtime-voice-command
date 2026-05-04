import queue
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import json
import commands

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

        if commands.speaking:
            continue

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = commands.normalize(result.get("text", ""))

            if not text:
                continue

            print("🗣️", text)

            if text in commands.ignored_phrases:
                continue

            if (wake_word in text or "im peter" in text) and not awake:
                awake = True
                commands.speak("Yes?")
                recognizer.Reset()
                print("✅Wake word detected")
                continue

            if awake:
                recognizer.Reset()
                commands.handle_command(text)
                awake = False

            if "hello" in text:
                commands.speak("What's up Muluken?")

            
            if "yeah no" in text:
                commands.speak("Yerosat isa doormii keetii sanamoo")
            
            if "thank you" in text:
                commands.speak("you're welcome")
                print("you're welcome")

        else:
            partial = json.loads(recognizer.PartialResult())
            if partial.get("partial"):
                print("...", partial["partial"])