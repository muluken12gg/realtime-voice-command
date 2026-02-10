import queue
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import json
import webbrowser
import os
import subprocess
from pycaw.pycaw import AudioUtilities
import re
import time

speaking = False
ignored_phrases = {
    "yes",
    "yeah",
}

def speak(text):
    global speaking
    speaking = True

    text = text.replace('"','`"')
    ps =f'''
        Add-Type -AssemblyName System.Speech
        $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $speak.Speak("{text}")
    '''
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", ps],
        stdout = subprocess.DEVNULL,
        stderr = subprocess.DEVNULL
    )

    time.sleep(0.4)
    speaking = False

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def set_volume(change):
    volume = AudioUtilities.GetSpeakers().EndpointVolume

    current = volume.GetMasterVolumeLevelScalar()

    if change == "up":
        volume.SetMasterVolumeLevelScalar(min(current + 0.1, 1.0), None)
    elif change == "down":
        volume.SetMasterVolumeLevelScalar(max(current - 0.1, 0.0), None)
    elif change == "mute":
        volume.SetMute(1, None)

def handle_command(text):
    if "volume up" in text:
        set_volume("up")
        speak("volume increased")
        print("🔊Volume up")
    elif "volume down" in text:
        set_volume("down")
        speak("volume decreased")
        print("🔉Volume down")
    elif "mute" in text:
        set_volume("mute")
        speak("muted")
        print("🔇Muted")
    elif "open notepad" in text:
        subprocess.Popen("notepad.exe")
        speak("opening notepad")
        print("📝Notepad opened")
    elif "open calculator" in text:
        subprocess.Popen("calc.exe")
        speak("opening calculator")
        print("🧮Calculator opened")
    elif "open folder" in text:
        os.startfile(os.path.expanduser("~"))
        speak("opening folder")
        print("📂Folder opened")

    elif ("open" in text) and ("code" in text or "call" in text or "Called" in text):
        subprocess.Popen(["cmd", "/c", "start", "code"])
        speak("opening visual studio code")
        print("🧑‍💻VS code opened")

    elif ("open" in text) and ("word" in text or "world" in text or "war" in text):
        subprocess.Popen(["cmd", "/c", "start", "winword"])

    elif "open tracker" in text:
        subprocess.Popen(["cmd", "/c", "start", "excel"])

    elif "okay" in text:
        subprocess.Popen([
            "explorer.exe",
            "shell:AppsFolder\\61284Wimberry.FlashQuiz_ycy428092yk7c!App"
        ])

    elif "open browser" in text:
        webbrowser.open("https://google.com")
        speak("opening browser")
        print("🌐Opening browser")

    elif ("open" in text) and ("youtube" in text or "you too" in text):
        webbrowser.open("https://youtube.com")
        speak("opening youtube")
        print("⏯️Opening YouTube")
    elif "shut down" in text:
        print("⚠️Shutdown command blocked(safety)")
    else:
        speak("command not recognized")
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

        if speaking:
            continue

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = normalize(result.get("text", ""))

            if not text:
                continue

            print("🗣️", text)

            if text in ignored_phrases:
                continue

            if wake_word in text and not awake:
                awake = True
                speak("Yes?")
                recognizer.Reset()
                print("✅Wake word detected")
                continue

            if awake:
                recognizer.Reset()
                handle_command(text)
                awake = False

        else:
            partial = json.loads(recognizer.PartialResult())
            if partial.get("partial"):
                print("...", partial["partial"])