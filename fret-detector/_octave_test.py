"""Testa a correção de oitava do YIN com 2º harmônico dominante (causa do bug E2→E3)."""
import sys
import numpy as np
from fret_detector import yin, freq_to_midi, midi_to_note

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
N = 4096
t = np.arange(N) / SR


def synth(f0, harm_amps):
    sig = np.zeros(N, dtype=np.float32)
    for n, a in enumerate(harm_amps, start=1):
        sig += a * np.sin(2 * np.pi * n * f0 * t)
    return (sig * np.exp(-1.5 * t)).astype(np.float32)


print(f"{'caso':<42} {'esperado':<8} {'detectado':>10}  {'nota':<5} {'status'}")
print("-" * 90)

cases = [
    # (label, f0, harm_amps, expected_hz)
    ("E2 normal (fund dominante)",        82.41, [1.0, 0.6, 0.4, 0.2], 82.41),
    ("E2 com 2o harm DOMINANTE (bug!)",   82.41, [0.3, 1.0, 0.5, 0.3], 82.41),
    ("E2 com 2o harm MUITO forte",        82.41, [0.15, 1.0, 0.6, 0.4], 82.41),
    ("A2 com 2o harm dominante",          110.0, [0.3, 1.0, 0.5, 0.2], 110.0),
    ("E3 REAL (não deve virar E2)",       164.81, [1.0, 0.6, 0.3], 164.81),
    ("E4 agudo normal",                   329.63, [1.0, 0.5, 0.2], 329.63),
    ("G3 fund fraca + 3o harm forte",     196.0, [0.4, 0.5, 1.0, 0.3], 196.0),
]

passed = 0
for label, f0, amps, expected in cases:
    sig = synth(f0, amps)
    detected = yin(sig, SR)
    if detected > 0:
        midi = int(round(freq_to_midi(detected)))
        note = midi_to_note(midi)
        # aceita se está dentro de 50 cents do esperado
        cents = 1200 * np.log2(detected / expected) if detected > 0 else 9999
        ok = abs(cents) < 50
    else:
        note, cents, ok = "?", 9999, False
    passed += int(ok)
    status = "✓" if ok else f"✗ ({cents:+.0f}¢)"
    print(f"{label:<42} {expected:>7.1f}  {detected:>9.2f}  {note:<5} {status}")

print(f"\n{passed}/{len(cases)} casos OK")
if passed == len(cases):
    print("✅ Correção de oitava funcionando — E2 não vira mais E3.")
else:
    print("⚠️  Alguns casos falharam — revisar fator de correção.")
