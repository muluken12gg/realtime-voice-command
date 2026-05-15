# real_time-voice-command-system
A system to command computer to do tasks with voice

## Project structure
- `voice_cmd.py` — main entrypoint and audio loop
- `commands.py` — command parsing, actions, and voice responses
- `commands.json` — customizable app and folder aliases
- `Release/` — Whisper.cpp binaries
- `Release/models/` — Whisper models

## Transcription
Uses Whisper.cpp for speech-to-text transcription.

## Model
Place the Whisper medium model as `Release/models/ggml-medium.bin`

## New feature
- Added voice search support: say `search for ...` or `google ...` and the assistant opens a Google search in your browser.
- Added voice website opening: say `open website example dot com`, `open site github`, or `open page stackoverflow`.
- Added voice YouTube search: say `search YouTube for cats`, `YouTube search for music`, or `YouTube funny videos`.
- Added voice calculator support: say `what is 5 plus 7`, `calculate 12 divided by 3`, or `compute 6 times 4`.
- Added voice time reporting: say `what time is it`, `current time`, or `tell me the time`.
