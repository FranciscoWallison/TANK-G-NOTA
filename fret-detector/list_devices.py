"""Lista dispositivos de entrada de áudio. Use isso para descobrir o ID do TANK-G."""
import sys
import sounddevice as sd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print(f"{'ID':<4} {'CHs':<4} {'Nome'}")
print("-" * 70)
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        print(f"{i:<4} {d['max_input_channels']:<4} {d['name']}")

print("\nDispositivo de entrada padrão:", sd.default.device[0])

candidates = [
    (i, d["name"]) for i, d in enumerate(sd.query_devices())
    if d["max_input_channels"] > 0
    and any(k in d["name"].lower() for k in ("usb-audio", "tank", "m-vave", "mvave"))
]
if candidates:
    print("\nProvável TANK-G:")
    for i, n in candidates:
        print(f"  → ID {i}: {n}")
else:
    print("\nNenhum dispositivo TANK-G/USB-Audio detectado. Conecte o pedal via USB-C e rode de novo.")
