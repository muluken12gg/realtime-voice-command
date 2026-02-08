import sounddevice as sd

print(sd.query_devices())
print("\n Default input devices:")
print(sd.query_devices(sd.default.device[3], 'input'))