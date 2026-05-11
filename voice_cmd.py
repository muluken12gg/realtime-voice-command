import subprocess
import commands

MODEL_PATH = "Release/models/ggml-medium.en.bin"
DEVICE_INDEX = 5

command = ["Release/whisper-stream.exe", "--model", MODEL_PATH, "--capture", str(DEVICE_INDEX), "--language", "en", "--step", "2000", "--length", "5000"]

proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

wake_word = "computer"
awake = False

print("🎤Listening... Speak now (Ctrl + C to stop)")

while True:
    line = proc.stdout.readline()
    if line == '' and proc.poll() is not None:
        break
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