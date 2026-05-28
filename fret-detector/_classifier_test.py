"""Sanity-test do classifier.py — sem calibração e com calibração mockada."""
import sys
import tempfile
import os
import numpy as np
from classifier import FretClassifier

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def fake_features(centroid_hz: float, hi_lo_db: float) -> np.ndarray:
    # [centroid, rolloff, zcr, B, h1_h2, hi_lo]
    return np.array([centroid_hz, centroid_hz * 1.6, 0.01, 0.001, 5.0, hi_lo_db], dtype=np.float32)


# ----- Teste 1: heurística sem calibração -----
print("== Teste 1: sem calibração (heurística por casa baixa) ==")
clf = FretClassifier()
# E4 (MIDI 64) pode ser tocado em 6 posições em standard
ranked = clf.classify(fake_features(800, 0), midi_note=64, tuning_name="standard")
print(f"  E4 → top {len(ranked)} candidatos:")
for s, f, c in ranked:
    print(f"    corda {s}, casa {f:2d} → conf {c*100:.1f}%")
assert ranked[0][1] == 0, "Sem calibração, top deve ser a casa mais baixa (0)"
print("  ✓ heurística prioriza casa baixa\n")

# ----- Teste 2: com calibração mockada -----
print("== Teste 2: com calibração mockada (E2 grave vs E4 aguda) ==")
clf = FretClassifier()
clf.tuning_name = "standard"

# Simula: cordas graves (5, 6) têm centroid baixo + hi_lo negativo
#          cordas agudas (1, 2) têm centroid alto + hi_lo positivo
for fret in [0, 5, 7, 12, 17]:
    clf.add_calibration_sample(6, fret, fake_features(200 + fret * 5, -10 + fret * 0.3))  # E grave
    clf.add_calibration_sample(5, fret, fake_features(250 + fret * 5, -8 + fret * 0.3))   # A grave
    clf.add_calibration_sample(4, fret, fake_features(350 + fret * 5, -5 + fret * 0.3))   # D
    clf.add_calibration_sample(3, fret, fake_features(500 + fret * 5, -2 + fret * 0.3))   # G
    clf.add_calibration_sample(2, fret, fake_features(700 + fret * 5, 1 + fret * 0.3))    # B
    clf.add_calibration_sample(1, fret, fake_features(900 + fret * 5, 4 + fret * 0.3))    # E aguda

print(f"  calibrado: {clf.n_calibrated_positions()} posições")

# Toca E4 (MIDI 64) com timbre BRILHANTE → deve ser corda 1 (E aguda solta)
feat_bright = fake_features(905, 4)
ranked = clf.classify(feat_bright, midi_note=64)
top = ranked[0]
print(f"  E4 brilhante → top: corda {top[0]}, casa {top[1]} (conf {top[2]*100:.1f}%)")
assert top[0] == 1, f"E4 brilhante deveria ser corda 1, foi {top[0]}"
print("  ✓ E4 brilhante → corda 1 (aguda)\n")

# Toca E4 (MIDI 64) com timbre ESCURO → deve ser corda mais grossa (6, casa 24 ou 5, casa 19)
feat_dark = fake_features(220, -8.5)
ranked = clf.classify(feat_dark, midi_note=64)
top = ranked[0]
print(f"  E4 escuro → top: corda {top[0]}, casa {top[1]} (conf {top[2]*100:.1f}%)")
assert top[0] in (5, 6), f"E4 escuro deveria ser corda 5 ou 6, foi {top[0]}"
print("  ✓ E4 escuro → corda grave\n")

# ----- Teste 3: persistência (save/load) -----
print("== Teste 3: save/load calibração ==")
with tempfile.TemporaryDirectory() as td:
    calib_path = os.path.join(td, "cal.json")
    clf.save_calibration(calib_path)
    clf2 = FretClassifier()
    ok = clf2.load(calib_path)
    assert ok, "load deveria retornar True"
    assert clf2.n_calibrated_positions() == clf.n_calibrated_positions()
    # mesma classificação deve dar mesmo resultado
    r1 = clf.classify(feat_bright, 64)
    r2 = clf2.classify(feat_bright, 64)
    assert r1[0] == r2[0], f"resultado divergente: {r1[0]} vs {r2[0]}"
    print(f"  ✓ salvou e carregou {clf2.n_calibrated_positions()} posições\n")

# ----- Teste 4: aprendizado online -----
print("== Teste 4: aprendizado online (correction) ==")
clf3 = FretClassifier()
clf3.tuning_name = "standard"
# zero calibração; só correções
feat_x = fake_features(400, -3)
clf3.learn_correction(feat_x, midi_note=64, correct_string=3, correct_fret=9)
# agora classifica algo MUITO parecido → deve ir pra (3, 9)
similar = fake_features(405, -3.1)
ranked = clf3.classify(similar, midi_note=64)
top = ranked[0]
print(f"  Após 1 correção: top = corda {top[0]}, casa {top[1]}")
assert top == (3, 9, top[2]) or top[0] == 3, f"top esperado (3, 9), foi {top}"
print(f"  ✓ correção aplicada\n")

print("Todos os sanity-checks do classifier passaram.")
