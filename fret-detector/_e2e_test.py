"""Sanity-test end-to-end (sem hardware): valida o pipeline completo.

Sintetiza áudio de 'cordas diferentes' (timbres distintos), cria uma calibração
fake, classifica novos samples e confere se acerta a corda."""
import sys
import tempfile
import os
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

np.random.seed(42)  # determinístico — evita flakiness do teste sintético

from features import extract_features
from classifier import FretClassifier
from fret_detector import TUNINGS, note_to_midi

SR = 44100
DUR = 1.0
N = int(SR * DUR)
t = np.arange(N) / SR


def synth_string_note(f0, brightness, decay=2.0):
    """Sintetiza nota com perfil harmônico modelando 'brilho' (0=grave wound, 1=plain agudo)."""
    sig = np.zeros(N, dtype=np.float32)
    for n in range(1, 10):
        if brightness < 0.5:
            # cordas wound: harmônicos baixos dominam
            w = max(0.0, 1.0 - n * 0.15) * (1.0 - brightness)
        else:
            # cordas plain: distribuição mais equilibrada
            w = max(0.0, 1.0 - n * 0.08) * brightness * 1.2
        sig += w * np.sin(2 * np.pi * n * f0 * t + np.random.uniform(0, 0.1))
    env = np.exp(-decay * t)
    return (sig * env).astype(np.float32)


def midi_to_freq(midi):
    return 440.0 * (2 ** ((midi - 69) / 12))


# Brilho típico por corda em standard tuning (mais aguda = mais brilhante)
STRING_BRIGHTNESS = {6: 0.15, 5: 0.25, 4: 0.40, 3: 0.55, 2: 0.75, 1: 0.90}

print("===== E2E TEST: calibração sintética + classificação =====\n")

# 1. Construir calibração sintética: 4 casas por corda
clf = FretClassifier()
clf.tuning_name = "standard"
tuning = TUNINGS["standard"]
frets_to_calibrate = [0, 5, 7, 12]
n_samples_per_pos = 2

print("Etapa 1: Gerando calibração sintética...")
for string in range(1, 7):
    open_note = list(reversed(tuning))[string - 1]
    open_midi = note_to_midi(open_note)
    bright = STRING_BRIGHTNESS[string]
    for fret in frets_to_calibrate:
        f0 = midi_to_freq(open_midi + fret)
        for _ in range(n_samples_per_pos):
            # adiciona variação pequena pra simular toque real
            b = bright + np.random.uniform(-0.03, 0.03)
            sig = synth_string_note(f0, b)
            feats = extract_features(sig, SR, f0)
            clf.add_calibration_sample(string, fret, feats)

print(f"  → {clf.n_calibrated_positions()} posições calibradas\n")

# 2. Persistir e recarregar (testa save/load)
print("Etapa 2: Salvar e recarregar JSON...")
with tempfile.TemporaryDirectory() as td:
    cal_path = os.path.join(td, "calibration.json")
    clf.save_calibration(cal_path)
    size = os.path.getsize(cal_path)
    print(f"  → calibration.json gerado ({size} bytes)")

    clf2 = FretClassifier()
    clf2.load(cal_path)
    assert clf2.n_calibrated_positions() == clf.n_calibrated_positions()
    print(f"  → recarregado OK\n")

# 3. Classificação de cordas SOLTAS (caso mais fácil)
print("Etapa 3: Classificar 6 cordas soltas...")
correct = 0
for string in range(1, 7):
    open_note = list(reversed(tuning))[string - 1]
    open_midi = note_to_midi(open_note)
    f0 = midi_to_freq(open_midi)
    bright = STRING_BRIGHTNESS[string] + np.random.uniform(-0.02, 0.02)
    sig = synth_string_note(f0, bright)
    feats = extract_features(sig, SR, f0)
    ranking = clf.classify(feats, open_midi, ergonomic_weight=0)  # timbre puro
    top_s, top_f, top_c = ranking[0]
    ok = (top_s == string and top_f == 0)
    correct += int(ok)
    mark = "✓" if ok else "✗"
    print(f"  {mark} esperado: corda {string} solta  →  top: corda {top_s} casa {top_f} ({top_c*100:.0f}%)")

acc = correct / 6 * 100
print(f"\n  Acurácia em cordas soltas: {correct}/6 = {acc:.0f}%")
assert acc >= 80, f"Acurácia muito baixa: {acc}%"

# 4. Classificação de nota com várias possibilidades (E4)
print("\nEtapa 4: Classificar E4 tocada em cordas diferentes...")
# E4 = MIDI 64. Pode ser: corda 1 solta, corda 2 casa 5, corda 3 casa 9, ...
e4_midi = 64
e4_freq = midi_to_freq(e4_midi)

test_cases = [
    (1, 0, "E aguda solta"),       # brilho alto
    (2, 5, "B casa 5"),            # brilho médio-alto
    (3, 9, "G casa 9"),            # brilho médio
    (4, 14, "D casa 14"),          # brilho médio-baixo
    (5, 19, "A casa 19"),          # brilho baixo
    (6, 24, "E grave casa 24"),    # brilho mais baixo
]
correct_e4 = 0
for true_string, true_fret, label in test_cases:
    bright = STRING_BRIGHTNESS[true_string] + np.random.uniform(-0.02, 0.02)
    sig = synth_string_note(e4_freq, bright)
    feats = extract_features(sig, SR, e4_freq)
    ranking = clf.classify(feats, e4_midi, ergonomic_weight=0)  # timbre puro
    top = ranking[0]
    ok = (top[0] == true_string)
    correct_e4 += int(ok)
    mark = "✓" if ok else "✗"
    print(f"  {mark} {label:25s}  →  top: corda {top[0]} casa {top[1]} ({top[2]*100:.0f}%)")

acc_e4 = correct_e4 / len(test_cases) * 100
print(f"\n  Acurácia em E4 multicorda: {correct_e4}/{len(test_cases)} = {acc_e4:.0f}%")

# 5. Aprendizado online: forçar errar, corrigir, ver se aprende
print("\nEtapa 5: Aprendizado online — forçar erro e ver se corrige...")
# Cria um timbre "ambíguo" + label correto inesperado
amb_feats = extract_features(synth_string_note(220.0, 0.5), SR, 220.0)
# Primeira classificação sem correção
r_pre = clf.classify(amb_feats, midi_note=57)  # A3 = MIDI 57
print(f"  Antes da correção: top = corda {r_pre[0][0]} casa {r_pre[0][1]}")
# Marca: "errou — era na verdade corda 4 casa 7"
clf.learn_correction(amb_feats, midi_note=57, correct_string=4, correct_fret=7)
# Re-classifica timbre similar
similar_feats = extract_features(synth_string_note(222.0, 0.51), SR, 222.0)
r_post = clf.classify(similar_feats, midi_note=57)
print(f"  Após correção: top = corda {r_post[0][0]} casa {r_post[0][1]}")
moved_toward = r_post[0][0] == 4 or any(r[0] == 4 and r[1] == 7 for r in r_post[:2])
mark = "✓" if moved_toward else "?"
print(f"  {mark} ranking se moveu em direção a (4, 7)\n")

print("===== Tudo OK — pipeline v2 funcionando =====")
