import json
import webbrowser
import os
import subprocess
from pathlib import Path
from pycaw.pycaw import AudioUtilities
import re
import time
from urllib.parse import quote_plus
from datetime import datetime

CONFIG_PATH = Path(__file__).with_name("commands.json")

def load_config():
    if not CONFIG_PATH.exists():
        return {}

    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

_config = load_config()
app_aliases = _config.get("app_aliases", {
    "vscode": "code",
    "word": "winword",
    "excel": "excel",
})
folder_aliases = _config.get("folder_aliases", {
    "home": "~",
    "documents": "~/Documents",
    "downloads": "~/Downloads",
})

speaking = False
ignored_phrases = {
    "yes",
    "yeah",
    # Placeholder when a chunk has no usable speech (silence / dropped audio).
    "blank audio",
    "blankaudio",
}

def speak(text):
    global speaking
    speaking = True

    text = text.replace('"', '`"')
    ps = f'''
        Add-Type -AssemblyName System.Speech
        $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $speak.Speak("{text}")
    '''
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", ps],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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


def open_alias_app(text):
    if not text.startswith("open "):
        return False

    target = text[len("open "):].strip()
    command = app_aliases.get(target)
    if not command:
        return False

    if command.startswith("http://") or command.startswith("https://"):
        webbrowser.open(command)
    elif os.path.isfile(os.path.expanduser(command)):
        subprocess.Popen(os.path.expanduser(command))
    else:
        subprocess.Popen(["cmd", "/c", "start", command])

    speak(f"opening {target}")
    print(f"📎Opening app alias: {target} -> {command}")
    return True


def open_alias_folder(text):
    if not text.startswith("open "):
        return False

    target = text[len("open "):].strip()
    path = folder_aliases.get(target)
    if not path:
        return False

    folder = os.path.expanduser(path)
    os.startfile(folder)
    speak(f"opening {target} folder")
    print(f"📁Opening folder: {target} -> {folder}")
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


def calculate_expression(text):
    expression = text
    matched = False
    for prefix in ("what is ", "calculate ", "compute "):
        if expression.startswith(prefix):
            expression = expression[len(prefix):]
            matched = True
            break
    if not matched:
        return False

    expression = expression.replace("plus", "+")
    expression = expression.replace("minus", "-")
    expression = expression.replace("times", "*")
    expression = expression.replace("multiplied by", "*")
    expression = expression.replace("x", "*")
    expression = expression.replace("divided by", "/")
    expression = expression.replace("over", "/")
    expression = re.sub(r"[^0-9\.\+\-\*\/\s]", "", expression)
    expression = re.sub(r"\s+", " ", expression).strip()

    if not expression:
        return False
    # Block "what is 2" / TTS junk; require an actual operation.
    if re.fullmatch(r"-?\d+(?:\.\d+)?", expression):
        return False
    if not re.search(r"[\+\-\*\/]", expression):
        return False

    try:
        result = eval(expression, {"__builtins__": None}, {})
    except Exception:
        return False

    speak(f"The answer is {result}")
    print(f"🧮Calculation: {expression} = {result}")
    return True


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
            "shell:AppsFolder\\61284Wimberry.FlashQuiz_ycy428092yk7c!App",
        ])
    elif "open book" in text:
        subprocess.Popen([r"C:\Users\HP\AppData\Local\SumatraPDF\SumatraPDF.exe"])
    elif open_alias_folder(text):
        pass
    elif open_alias_app(text):
        pass
    elif open_website(text):
        pass
    elif calculate_expression(text):
        pass
    elif search_youtube(text):
        pass
    elif search_google(text):
        pass
    elif "open browser" in text:
        webbrowser.open("https://google.com")
        speak("opening browser")
        print("🌐Opening browser")
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
