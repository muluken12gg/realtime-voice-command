# real_time-voice-command-system
A system to command computer to do tasks with voice.

## Project structure
- `voice_cmd.py` — main entrypoint and audio loop
- `commands.py` — command parsing, actions, and voice responses
- `commands.json` — customizable app and folder aliases
- `desktop_app/` — Flutter desktop control panel application
- `Release/` — Whisper.cpp binaries
- `Release/models/` — Whisper models

## Desktop Control Panel (GUI)
A modern Flutter desktop interface is available in `desktop_app/`:
- **Auto Startup**: Option to automatically start when Windows boots up.
- **System Tray Support**: Minimizes and runs quietly in the Windows system tray when closed.
- **Global Shortcut**: Press `Ctrl + Alt + Space` anywhere to instantly open the control panel.
- **Voice Control Toggle**: Pause or resume voice command listening with a single toggle switch.
- **Command Management**: Direct access to edit `commands.json`.

To run the Flutter app locally:
```bash
cd desktop_app
flutter run -d windows
```

## Transcription
Uses Whisper.cpp for speech-to-text transcription.

## Model
Place the Whisper medium model as `Release/models/ggml-medium.bin`

## Features
- **Voice Search**: Say `search for ...` or `google ...` to search Google.
- **Website Opening**: Say `open website example.com`, `open site github`, or `open page stackoverflow`.
- **YouTube Search**: Say `search YouTube for cats` or `YouTube funny videos`.
- **Calculator**: Say `what is 5 plus 7`, `calculate 12 divided by 3`, or `compute 6 times 4`.
- **Time Reporting**: Say `what time is it`, `current time`, or `tell me the time`.

