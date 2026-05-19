import sounddevice as sd

print(" Listing all available audio devices...\n")
print(sd.query_devices())

print("\n Default input device index:", sd.default.device[0])
print(" Default output device index:", sd.default.device[1])

device_info = sd.query_devices(sd.default.device[0])
print("\n Default input sample rate:", device_info['default_samplerate'])
