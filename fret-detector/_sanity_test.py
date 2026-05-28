"""Teste sintético do pitch detection — não precisa de hardware."""
from fret_detector import yin, freq_to_midi, midi_to_note, fret_positions, TUNINGS
import numpy as np

sr = 44100
# notas das 6 cordas soltas em standard tuning
test_freqs = {
    82.41: "E2 (6ª solta)",
    110.0: "A2 (5ª solta)",
    146.83: "D3 (4ª solta)",
    196.0: "G3 (3ª solta)",
    246.94: "B3 (2ª solta)",
    329.63: "E4 (1ª solta)",
    440.0: "A4 (2ª casa 10)",
    659.25: "E5 (1ª casa 12)",
}

print(f"{'expected Hz':<14} {'expected note':<20} {'detected':>10} {'err':>7}  {'nota':<5} posições")
print("-" * 110)
for test_freq, label in test_freqs.items():
    t = np.arange(2048) / sr
    sig = (np.sin(2 * np.pi * test_freq * t) * 0.5).astype(np.float32)
    detected = yin(sig, sr)
    if detected > 0:
        midi = int(round(freq_to_midi(detected)))
        note = midi_to_note(midi)
        err = detected - test_freq
        pos = fret_positions(midi, TUNINGS["standard"])
    else:
        midi, note, err, pos = 0, "?", 0, []
    print(f"{test_freq:>10.2f}    {label:<20} {detected:>10.2f} {err:>+7.2f}  {note:<5} {pos}")
