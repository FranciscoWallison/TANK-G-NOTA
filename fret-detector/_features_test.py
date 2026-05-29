"""Sanity-test do features.py (v2, 8 features) com notas sintéticas.

Verifica:
  - vetor tem N_FEATURES = 8
  - brightness/centroid discriminam corda brilhante vs escura
  - sustain_ratio discrimina sustain longo (solta) vs curto (pressionada)
"""
import sys
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from features import extract_features, FEATURE_NAMES, N_FEATURES, features_dict, FEATURE_SET

SR = 44100


def synth_note(f0, rolloff, decay=1.5, dur=0.6, n_harm=40):
    """Nota sintética: rolloff^(n-1) por harmônico (rolloff alto = mais brilho)
    + envelope exp(-decay·t). Inclui harmônicos altos p/ cobrir 2-4kHz."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for k in range(1, n_harm + 1):
        if k * f0 >= SR / 2:
            break
        sig += (rolloff ** (k - 1)) * np.sin(2 * np.pi * k * f0 * t)
    return (sig * np.exp(-decay * t)).astype(np.float32)


print(f"===== FEATURES TEST ({FEATURE_SET}, {N_FEATURES} features) =====\n")
assert N_FEATURES == 8, f"esperava 8 features, veio {N_FEATURES}"

# corda escura (rolloff baixo: poucos harmônicos altos) vs brilhante (rolloff alto)
dark = synth_note(110.0, rolloff=0.55, decay=1.5)
bright = synth_note(110.0, rolloff=0.92, decay=1.5)
fd = features_dict(extract_features(dark, SR, 110.0))
fb = features_dict(extract_features(bright, SR, 110.0))

print(f"{'feature':<22} {'escura':>10} {'brilhante':>10}")
for name in FEATURE_NAMES:
    print(f"{name:<22} {fd[name]:>10.3f} {fb[name]:>10.3f}")
print()

ok_bright = fb["brightness_index"] > fd["brightness_index"]
print(f"brightness brilhante > escura: {fb['brightness_index']:.1f} > {fd['brightness_index']:.1f}  "
      f"{'OK' if ok_bright else 'FAIL'}")
assert ok_bright, "brightness_index deveria separar brilhante de escura"

ok_centroid = fb["centroid_normalized"] > fd["centroid_normalized"]
print(f"centroid_norm brilhante > escura: {fb['centroid_normalized']:.2f} > {fd['centroid_normalized']:.2f}  "
      f"{'OK' if ok_centroid else 'FAIL'}")
assert ok_centroid

# sustain: solta (decay lento) vs pressionada (decay rápido)
print()
opn = synth_note(110.0, rolloff=0.7, decay=0.8)   # sustenta
fret = synth_note(110.0, rolloff=0.7, decay=6.0)  # decai rápido
s_open = features_dict(extract_features(opn, SR, 110.0))["sustain_ratio"]
s_fret = features_dict(extract_features(fret, SR, 110.0))["sustain_ratio"]
print(f"sustain_ratio  solta={s_open:.3f}  pressionada={s_fret:.3f}")
assert s_open > s_fret * 2, f"solta deveria sustentar muito mais ({s_open} vs {s_fret})"
print("  ✓ sustain_ratio separa solta de pressionada\n")

print("✅ features.py (v2) discriminando corretamente.")
