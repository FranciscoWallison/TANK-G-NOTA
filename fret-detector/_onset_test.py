"""Testa OnsetDetector: silêncio → ataque → decay → silêncio → novo ataque.

Verifica que:
  - um ataque dispara UM onset com a nota certa
  - uma nota sustentada NÃO dispara vários onsets
  - só rearma após voltar ao silêncio

Os sinais são gerados com fase contínua (um array por cena, depois fatiado em
hops) — senão a junção entre blocos cria glitch e o YIN erra a oitava.
"""
import sys
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from audio_engine import OnsetDetector
from fret_detector import note_to_midi, SAMPLE_RATE

HOP = 1024


def tone(freq, amp, n_blocks):
    """Tom contínuo (fase coerente) com leve 2º harmônico, n_blocks * HOP samples."""
    n = n_blocks * HOP
    t = np.arange(n) / SAMPLE_RATE
    sig = amp * (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * 2 * freq * t))
    return sig.astype(np.float32)


def silence(n_blocks):
    return (np.random.randn(n_blocks * HOP) * 0.0005).astype(np.float32)


def feed_signal(det, signal, ts0=0.0):
    """Fatia o sinal em hops e empurra no detector. Retorna lista de onsets."""
    onsets = []
    dt = HOP / SAMPLE_RATE
    ts = ts0
    for i in range(0, len(signal) - HOP + 1, HOP):
        r = det.push(signal[i:i + HOP], ts)
        if r is not None:
            onsets.append(r)
        ts += dt
    return onsets


print("===== ONSET TEST =====\n")

E2 = note_to_midi("E2")
A2 = note_to_midi("A2")
fE2, fA2 = 82.41, 110.0

# Cena 1: silêncio, depois E2 sustentado
det = OnsetDetector()
sig = np.concatenate([silence(4), tone(fE2, 0.4, 12)])
onsets = feed_signal(det, sig)
print(f"Cena 1 (E2 sustentado): {len(onsets)} onset(s) → {onsets}")
assert len(onsets) == 1, f"esperava 1 onset, veio {len(onsets)}"
assert onsets[0][0] == E2, f"esperava E2={E2}, veio {onsets[0][0]}"
print("  ✓ 1 ataque, nota E2, sem disparo múltiplo no sustain\n")

# Cena 2: E2, silêncio, A2 → 2 onsets
det = OnsetDetector()
sig = np.concatenate([silence(3), tone(fE2, 0.4, 8), silence(4), tone(fA2, 0.4, 8)])
onsets = feed_signal(det, sig)
notes = [m for m, _ in onsets]
print(f"Cena 2 (E2, silêncio, A2): {len(onsets)} onsets → notas {notes}")
assert len(onsets) == 2, f"esperava 2 onsets, veio {len(onsets)}"
assert notes == [E2, A2], f"esperava [E2, A2], veio {notes}"
print("  ✓ 2 ataques distintos detectados\n")

# Cena 3: nota fraca não dispara
det = OnsetDetector()
sig = np.concatenate([silence(3), tone(fE2, 0.01, 8)])
onsets = feed_signal(det, sig)
print(f"Cena 3 (nota fraca): {len(onsets)} onset(s)")
assert len(onsets) == 0, f"nota fraca não devia disparar, veio {len(onsets)}"
print("  ✓ ataque fraco ignorado\n")

# Cena 4: troca de nota sem silêncio NÃO redispara
det = OnsetDetector()
sig = np.concatenate([silence(3), tone(fE2, 0.4, 6), tone(fA2, 0.4, 6)])
onsets = feed_signal(det, sig)
print(f"Cena 4 (troca sem silêncio): {len(onsets)} onset(s) → {[m for m,_ in onsets]}")
assert len(onsets) == 1, f"sem silêncio entre notas não deve redisparar, veio {len(onsets)}"
print("  ✓ exige silêncio pra rearmar\n")

print("✅ Todos os testes de onset passaram.")
