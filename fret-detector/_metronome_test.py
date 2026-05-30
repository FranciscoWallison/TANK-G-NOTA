"""Sanity-test do metrônomo: renderiza N blocos offline e verifica que clicks
aparecem nas posições esperadas pra um BPM dado."""
import sys
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from audio_engine import AudioEngine
from fret_detector import HOP_SIZE, SAMPLE_RATE

print("===== METRONOME TEST =====\n")

eng = AudioEngine(device=2)   # device só pra construir; não vamos start()
eng.metronome_on = True
eng.metronome_bpm = 120        # 0.5s/beat = 22050 samples
eng.metronome_accent_every = 4

# simula 2s de áudio (88200 samples) em blocos de HOP_SIZE
spb = SAMPLE_RATE * 60.0 / eng.metronome_bpm
total_samples = int(2.0 * SAMPLE_RATE)
blocks = total_samples // HOP_SIZE

print(f"BPM={eng.metronome_bpm}  spb={spb:.0f} samples  blocks={blocks}")

beats_detected = []
eng._metro_sample = 0
for b in range(blocks):
    out = np.zeros((HOP_SIZE, 2), dtype=np.float32)
    eng._render_metronome(out, HOP_SIZE)
    peak = float(np.max(np.abs(out)))
    if peak > 0.1:                  # click presente nesse bloco
        # acha a amostra de pico (início do click neste bloco)
        i = int(np.argmax(np.abs(out[:, 0])))
        abs_pos = eng._metro_sample + i
        beats_detected.append(abs_pos)
    eng._metro_sample += HOP_SIZE

print(f"\nClicks detectados em (amostra): {beats_detected}")

# beats esperados em 2s @ 120 BPM: 0, 22050, 44100, 66150 (4 beats)
expected = [int(round(k * spb)) for k in range(int(2.0 * eng.metronome_bpm / 60))]
print(f"Beats esperados:           {expected}")

# cada click detectado deve estar perto de um beat esperado (±HOP_SIZE)
ok = 0
for exp in expected:
    if any(abs(d - exp) <= HOP_SIZE for d in beats_detected):
        ok += 1
print(f"\n{ok}/{len(expected)} beats no tempo certo (±{HOP_SIZE} samples)")
assert ok == len(expected), "metrônomo perdeu/atrasou beats"
print("✅ Metrônomo dispara clicks no tempo correto.\n")


# ===== caso 2: beat_offset desloca o acento =====
# accent_every=4, beat_offset=3 → acento em k=3, 7, 11... (NÃO em k=0)
print("===== beat_offset shifts accent =====")
eng2 = AudioEngine(device=2)
eng2.metronome_on = True
eng2.metronome_bpm = 120
eng2.metronome_accent_every = 4
eng2.metronome_beat_offset = 3
spb2 = SAMPLE_RATE * 60.0 / eng2.metronome_bpm
total2 = int(2.0 * SAMPLE_RATE)
blocks2 = total2 // HOP_SIZE

# colhe (beat_k, peak_amplitude) por click detectado
clicks = []   # (beat_k, peak)
eng2._metro_sample = 0
for b in range(blocks2):
    out = np.zeros((HOP_SIZE, 2), dtype=np.float32)
    eng2._render_metronome(out, HOP_SIZE)
    peak = float(np.max(np.abs(out)))
    if peak > 0.1:
        i = int(np.argmax(np.abs(out[:, 0])))
        abs_pos = eng2._metro_sample + i
        k = int(round(abs_pos / spb2))
        clicks.append((k, peak))
    eng2._metro_sample += HOP_SIZE

# accent_amp ~0.85*gain, normal ~0.6*gain → accent peak ≈ 1.4x normal
peaks_by_k = {k: p for k, p in clicks}
normal_peak = peaks_by_k.get(0)
accent_peak = peaks_by_k.get(3)
print(f"  peak no beat 0 (deve ser NORMAL): {normal_peak}")
print(f"  peak no beat 3 (deve ser ACENTO): {accent_peak}")
assert normal_peak and accent_peak and accent_peak > normal_peak * 1.2, \
    f"acento deveria ser >20% mais alto: normal={normal_peak}, accent={accent_peak}"
print("  ✓ acento deslocado p/ beat 3 (não cai no beat 0)\n")
print("✅ beat_offset desloca o acento corretamente.")
