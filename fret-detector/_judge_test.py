"""Testa a lógica pura do jogo: judge() (janelas de timing) e build_notes()
(posição sugerida + lane). Não abre janela pygame."""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from game import judge, build_notes, suggest_position, PERFECT_MS, GOOD_MS
from charts import CHARTS
from fret_detector import TUNINGS, note_to_midi

print("===== JUDGE / BUILD TEST =====\n")

# ---- judge() ----
print("judge():")
cases = [
    (0, "perfect"), (PERFECT_MS - 1, "perfect"), (-PERFECT_MS + 1, "perfect"),
    (PERFECT_MS + 1, "good"), (GOOD_MS - 1, "good"), (-(GOOD_MS - 1), "good"),
    (GOOD_MS + 1, None), (500, None), (-500, None),
]
for delta, expected in cases:
    got = judge(delta)
    mark = "✓" if got == expected else "✗"
    print(f"  {mark} judge({delta:+5} ms) = {str(got):<8} (esperado {expected})")
    assert got == expected, f"judge({delta}) = {got}, esperado {expected}"
print("  ✓ janelas de timing corretas\n")

# ---- suggest_position() — escolhe casa mais baixa ----
print("suggest_position() (standard):")
std = TUNINGS["standard"]
sp_cases = [
    ("E2", (6, 0)),    # só existe na 6ª solta
    ("A2", (5, 0)),    # 5ª solta (vs 6ª casa 5) → escolhe solta
    ("D3", (4, 0)),    # 4ª solta
    ("E4", (1, 0)),    # 1ª solta
]
for note, expected in sp_cases:
    pos = suggest_position(note_to_midi(note), std)
    mark = "✓" if pos == expected else "✗"
    print(f"  {mark} {note}: {pos} (esperado {expected})")
    assert pos == expected, f"{note}: {pos} != {expected}"
print("  ✓ sugere a posição mais ergonômica (menor casa)\n")

# ---- build_notes() — lane = 6 - string, tempos crescentes ----
print("build_notes() (escala_mi):")
chart = CHARTS["escala_mi"]
notes = build_notes(chart, chart.tuning)
assert len(notes) == len(chart.notes), "contagem de notas diverge"
# tempos estritamente crescentes
times = [n.hit_time for n in notes]
assert all(b > a for a, b in zip(times, times[1:])), "hit_times não crescentes"
# lanes no range 0..5
assert all(0 <= n.lane <= 5 for n in notes), "lane fora do range"
# 1ª nota é E2 → corda 6 → lane 0
n0 = notes[0]
print(f"  1ª nota: {n0.name} corda {n0.string_num} casa {n0.fret} → lane {n0.lane} @ {n0.hit_time:.2f}s")
assert n0.name == "E2" and n0.string_num == 6 and n0.lane == 0
print(f"  {len(notes)} notas, tempos crescentes, lanes válidas")
print("  ✓ build_notes OK\n")

print("✅ Todos os testes de julgamento/construção passaram.")
