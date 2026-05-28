"""Sanity-test do features.py — compara timbres sintéticos.

Cordas wound (grossas) têm mais energia em harmônicos baixos e ataque menos brilhante.
Vamos simular dois timbres e ver se as features capturam a diferença.
"""
import sys
import numpy as np
from features import extract_features, FEATURE_NAMES, features_dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 44100
DUR = 0.5
N = int(SR * DUR)
t = np.arange(N) / SR


def synth(f0, harm_weights, decay=2.0):
    """Sintetiza nota com pesos dados aos harmônicos. decay aplica envelope."""
    sig = np.zeros(N, dtype=np.float32)
    for n, w in enumerate(harm_weights, start=1):
        sig += w * np.sin(2 * np.pi * n * f0 * t)
    env = np.exp(-decay * t)
    return (sig * env).astype(np.float32)


print(f"{'tipo':<25} | " + " | ".join(f"{n:>10}" for n in FEATURE_NAMES))
print("-" * 115)

cases = [
    # Corda grave wound: harmônicos baixos dominam
    ("E2 grave (wound, ricos)", 82.41, [1.0, 0.9, 0.7, 0.5, 0.3, 0.2, 0.1, 0.05]),
    # Mesma nota mas em corda fina + casa alta: harmônicos mais equilibrados, mais brilho
    ("E2 brilhante (plain)",    82.41, [1.0, 0.4, 0.3, 0.4, 0.5, 0.4, 0.3, 0.2]),
    # Corda aguda E4
    ("E4 aguda",                329.63, [1.0, 0.7, 0.4, 0.2, 0.1, 0.05, 0.02, 0.01]),
    # E4 com mais brilho (plain string)
    ("E4 mais brilhante",       329.63, [1.0, 0.6, 0.5, 0.5, 0.4, 0.3, 0.2, 0.1]),
]

results = []
for label, f0, weights in cases:
    sig = synth(f0, weights)
    feats = extract_features(sig, SR, f0)
    results.append((label, feats))
    vals = " | ".join(f"{v:10.3f}" for v in feats)
    print(f"{label:<25} | {vals}")

print()
print("Sanity-checks esperados:")

# 1) E2 grave deve ter centroid mais BAIXO que E2 brilhante
c_grave = results[0][1][0]
c_bril = results[1][1][0]
ok1 = c_grave < c_bril
print(f"  E2 grave centroid < E2 brilhante: {c_grave:.0f} < {c_bril:.0f}  {'OK' if ok1 else 'FAIL'}")

# 2) E2 grave deve ter hi/lo ratio MENOR (mais energia nos baixos)
hl_grave = results[0][1][5]
hl_bril = results[1][1][5]
ok2 = hl_grave < hl_bril
print(f"  E2 grave hi/lo < E2 brilhante:   {hl_grave:+.1f} dB < {hl_bril:+.1f} dB  {'OK' if ok2 else 'FAIL'}")

# 3) E4 deve ter centroid maior que E2
c_e2 = results[0][1][0]
c_e4 = results[2][1][0]
ok3 = c_e4 > c_e2
print(f"  E4 centroid > E2:                {c_e4:.0f} > {c_e2:.0f}  {'OK' if ok3 else 'FAIL'}")

if ok1 and ok2 and ok3:
    print("\n✅ features.py discriminando timbres corretamente.")
else:
    print("\n❌ Alguma feature não discriminou — revisar.")
