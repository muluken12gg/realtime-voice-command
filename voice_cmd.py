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
from urllib.parse import quote_plus
from datetime import datetime

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

def search_google(text):
    query = None

    if text.startswith("search for "):
        query = text[len("search for "):].strip()
    elif text.startswith("google "):
        query = text[len("google "):].strip()
    else:
        match = re.search(r"(?:search|google) (?:for )?(.*)", text)
        if match:
            query = match.group(1).strip()

    if query:
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        speak(f"searching google for {query}")
        print(f"🌐Searching Google for: {query}")
        return True

    return False

def search_youtube(text):
    query = None

    if text.startswith("search youtube for "):
        query = text[len("search youtube for "):].strip()
    elif text.startswith("youtube search for "):
        query = text[len("youtube search for "):].strip()
    elif text.startswith("youtube "):
        query = text[len("youtube "):].strip()

    if query:
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        webbrowser.open(url)
        speak(f"searching YouTube for {query}")
        print(f"▶️Searching YouTube for: {query}")
        return True

    return False

def report_time():
    now = datetime.now()
    spoken = now.strftime("The time is %I:%M %p")
    speak(spoken)
    print(f"🕒{spoken}")
    return True

def open_website(text):
    match = re.search(r"open (?:website|site|page) (.+)", text)
    if not match:
        return False

    site = match.group(1).strip()
    site = site.replace(" dot ", ".").replace(" ", "")
    if not site:
        return False

    if not site.startswith("http://") and not site.startswith("https://"):
        site = f"https://{site}"

    webbrowser.open(site)
    speak(f"opening {site}")
    print(f"🌐Opening website: {site}")
    return True

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
    
    elif "thank you" in text:
        speak("")

    elif "fuck you" in text or "fuck him" in text:
        speak("fuck you too piece of shit!")

    elif ("open" in text) and ("code" in text or "call" in text or "Called" in text):
        subprocess.Popen(["cmd", "/c", "start", "code"])
        speak("opening visual studio code")
        print("🧑‍💻VS code opened")

    elif ("open" in text) and ("word" in text or "world" in text or "war" in text):
        subprocess.Popen(["cmd", "/c", "start", "winword"])

    elif "open tracker" in text:
        subprocess.Popen(["cmd", "/c", "start", "excel"])

    elif "open library" in text:
        subprocess.Popen([
            "explorer.exe",
            "shell:AppsFolder\\61284Wimberry.FlashQuiz_ycy428092yk7c!App"
        ])

    elif "open book" in text:
        subprocess.Popen([r"C:\Users\HP\AppData\Local\SumatraPDF\SumatraPDF.exe"])

    elif open_website(text):
        pass

    elif search_youtube(text):
        pass

    elif search_google(text):
        pass

    elif "open browser" in text:
        webbrowser.open("https://google.com")
        speak("opening browser")
        print("🌐Opening browser")

    elif "what time" in text or "current time" in text or "tell me the time" in text:
        report_time()

    elif ("open" in text) and ("youtube" in text or "you too" in text):
        webbrowser.open("https://youtube.com")
        speak("opening youtube")
        print("⏯️Opening YouTube")
    elif "shut down" in text:
        speak("hey, are you crazy? idiot, stupid number one.")
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

            if (wake_word in text or "im peter" in text) and not awake:
                awake = True
                speak("Yes?")
                recognizer.Reset()
                print("✅Wake word detected")
                continue

            if awake:
                recognizer.Reset()
                handle_command(text)
                awake = False

            if "hello" in text:
                speak("What's up Muluken?")

            
            if "yeah no" in text:
                speak("Yerosat isa doormii keetii sanamoo")
            
            if "thank you" in text:
                speak("you're welcome")
                print("you're welcome")

        else:
            partial = json.loads(recognizer.PartialResult())
            if partial.get("partial"):
                print("...", partial["partial"])