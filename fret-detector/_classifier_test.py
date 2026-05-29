"""Sanity-test do classifier.py (features v2, 8-D) — heurística, calibração,
persistência, aprendizado, versionamento e gate solta/pressionada."""
import sys
import json
import tempfile
import os
import numpy as np
from classifier import FretClassifier
from features import N_FEATURES

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def fake(bright: float, sustain: float = 0.5) -> np.ndarray:
    """Vetor 8-D: 'bright' controla brilho (corda aguda↔grave); 'sustain' controla
    solta(alto)↔pressionada(baixo). Demais features neutras."""
    # [brightness, tilt, centroid_norm, B, richness, decay, sustain, attack]
    return np.array([bright, -1.0, 3.0 + bright * 0.3, 0.001, 8.0, 1.3, sustain, 0.3],
                    dtype=np.float32)


assert N_FEATURES == 8

# ----- Teste 1: heurística sem calibração -----
print("== Teste 1: sem calibração (heurística por casa baixa) ==")
clf = FretClassifier()
ranked = clf.classify(fake(0), midi_note=64, tuning_name="standard")
assert ranked[0][1] == 0, "Sem calibração, top deve ser casa 0"
print(f"  ✓ heurística prioriza casa baixa (top casa {ranked[0][1]})\n")

# ----- Teste 2: com calibração mockada (brilho por corda) -----
print("== Teste 2: calibração mockada (corda grave escura ↔ aguda brilhante) ==")
clf = FretClassifier()
clf.tuning_name = "standard"
bright_by_string = {6: -10, 5: -6, 4: -2, 3: 2, 2: 6, 1: 10}
for fret in [0, 5, 7, 12, 17]:
    for s, b in bright_by_string.items():
        clf.add_calibration_sample(s, fret, fake(b + fret * 0.1))
print(f"  calibrado: {clf.n_calibrated_positions()} posições")

top = clf.classify(fake(10), midi_note=64)[0]   # E4 brilhante → corda 1
print(f"  E4 brilhante → corda {top[0]} casa {top[1]} ({top[2]*100:.1f}%)")
assert top[0] == 1, f"esperava corda 1, veio {top[0]}"

top = clf.classify(fake(-9), midi_note=64)[0]    # E4 escuro → corda grave
print(f"  E4 escuro → corda {top[0]} casa {top[1]} ({top[2]*100:.1f}%)")
assert top[0] in (5, 6), f"esperava 5/6, veio {top[0]}"
print("  ✓ timbre discrimina corda\n")

# ----- Teste 3: save/load + versionamento -----
print("== Teste 3: save/load + versão ==")
with tempfile.TemporaryDirectory() as td:
    calib_path = os.path.join(td, "cal.json")
    clf.save_calibration(calib_path)
    data = json.load(open(calib_path, encoding="utf-8"))
    assert data["n_features"] == 8 and data["feature_set"] == "v2", "metadados de versão faltando"

    clf2 = FretClassifier()
    assert clf2.load(calib_path) is True and not clf2.incompatible
    assert clf2.n_calibrated_positions() == clf.n_calibrated_positions()
    print(f"  ✓ salvou/carregou {clf2.n_calibrated_positions()} posições (v2)")

    # simula calibração ANTIGA (6 features) → incompatível
    data["n_features"] = 6
    json.dump(data, open(calib_path, "w", encoding="utf-8"))
    clf3 = FretClassifier()
    ok = clf3.load(calib_path)
    assert ok is False and clf3.incompatible, "deveria detectar incompatibilidade"
    print("  ✓ calibração antiga detectada como incompatível\n")

# ----- Teste 4: aprendizado online -----
print("== Teste 4: aprendizado online ==")
clf4 = FretClassifier()
clf4.tuning_name = "standard"
clf4.learn_correction(fake(0), midi_note=64, correct_string=3, correct_fret=9)
top = clf4.classify(fake(0.1), midi_note=64)[0]
print(f"  após correção: top corda {top[0]} casa {top[1]}")
assert top[0] == 3, f"correção não aplicada: {top}"
print("  ✓ correção aplicada\n")

# ----- Teste 5: gate solta/pressionada (open_hint) -----
print("== Teste 5: open_hint favorece solta/pressionada ==")
clf5 = FretClassifier()
clf5.tuning_name = "standard"
# calibra B3 (midi 59) em 2ª solta (2,0) e 3ª casa 4 (3,4), timbres parecidos
for _ in range(3):
    clf5.add_calibration_sample(2, 0, fake(6, sustain=0.8))   # solta sustenta
    clf5.add_calibration_sample(3, 4, fake(5.5, sustain=0.2)) # fretted seca
r_open = clf5.classify(fake(5.7, sustain=0.5), midi_note=59, open_hint=True)
r_fret = clf5.classify(fake(5.7, sustain=0.5), midi_note=59, open_hint=False)
print(f"  open_hint=True  → top {r_open[0][:2]}")
print(f"  open_hint=False → top {r_fret[0][:2]}")
assert r_open[0][1] == 0, "open_hint=True deveria favorecer casa 0 (solta)"
assert r_fret[0][1] != 0, "open_hint=False deveria favorecer fretted"
print("  ✓ gate solta/pressionada funciona\n")

print("Todos os sanity-checks do classifier passaram.")
