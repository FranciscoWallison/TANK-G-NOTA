"""Testa a discriminação SOLTA vs PRESSIONADA por sustain_ratio.

Corda solta sustenta muito mais (decay lento) que pressionada (decay rápido).
Verifica que um limiar simples em sustain_ratio separa os dois de forma confiável.
"""
import sys
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from features import extract_features, IDX_SUSTAIN

SR = 44100


def synth(f0, decay, dur=0.6, harm=(1.0, 0.7, 0.5, 0.3, 0.2)):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for k, w in enumerate(harm, start=1):
        sig += w * np.sin(2 * np.pi * k * f0 * t)
    return (sig * np.exp(-decay * t)).astype(np.float32)


print("===== OPEN vs FRETTED TEST =====\n")

# decays típicos: solta ~0.5-1.5, pressionada ~4-8
open_cases = [(82.41, 0.6), (110.0, 0.8), (146.83, 1.0), (196.0, 1.2)]
fret_cases = [(82.41, 5.0), (110.0, 6.0), (146.83, 5.5), (196.0, 7.0)]

open_sr = []
fret_sr = []
for f0, dc in open_cases:
    sr_val = float(extract_features(synth(f0, dc), SR, f0)[IDX_SUSTAIN])
    open_sr.append(sr_val)
    print(f"  SOLTA      f0={f0:6.1f} decay={dc:.1f} -> sustain_ratio={sr_val:.3f}")
for f0, dc in fret_cases:
    sr_val = float(extract_features(synth(f0, dc), SR, f0)[IDX_SUSTAIN])
    fret_sr.append(sr_val)
    print(f"  PRESSIONADA f0={f0:6.1f} decay={dc:.1f} -> sustain_ratio={sr_val:.3f}")

print()
min_open = min(open_sr)
max_fret = max(fret_sr)
print(f"menor sustain de SOLTA   = {min_open:.3f}")
print(f"maior sustain de FRETTED = {max_fret:.3f}")

# deve haver separação clara: todas as soltas > todas as fretted
assert min_open > max_fret, f"separação falhou: soltas {open_sr} vs fretted {fret_sr}"

# limiar no meio (geométrico) classifica 100%
threshold = (min_open * max_fret) ** 0.5
correct = sum(s > threshold for s in open_sr) + sum(s <= threshold for s in fret_sr)
total = len(open_sr) + len(fret_sr)
print(f"limiar={threshold:.3f} → {correct}/{total} corretos")
assert correct == total
print("\n✅ sustain_ratio separa solta de pressionada com 100% nos sintéticos.")
