"""Smoke test do jogo SEM display real (SDL dummy). Valida que:
  - Game inicializa headless
  - process_onset no tempo certo marca 'perfect' e pontua
  - nota que passa vira 'miss'
  - todos os _draw_* rodam sem crashar
"""
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"   # sem janela real
os.environ["SDL_AUDIODRIVER"] = "dummy"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from game import Game
from charts import CHARTS

print("===== GAME SMOKE TEST (headless) =====\n")

chart = CHARTS["escala_mi"]
g = Game(chart, chart.tuning, engine=None, audio_offset=0.0, show_hint=True, mock=True)
print(f"init OK — {len(g.notes)} notas, lane da 1ª = {g.notes[0].lane}")

# ---- Teste 1: acerto perfeito ----
target = g.notes[0]
# força o relógio pra que elapsed == hit_time da nota alvo (acerto perfeito)
g.start_wall = time.time() - (target.hit_time + g.pause_accum) - __import__("game").COUNTDOWN
ts = time.time()
g.process_onset(target.midi, ts)
print(f"após onset no tempo certo: result={target.result} score={g.score} combo={g.combo}")
assert target.result == "perfect", f"esperava perfect, veio {target.result}"
assert g.score == 100 and g.combo == 1
print("  ✓ acerto perfeito pontua\n")

# ---- Teste 2: nota errada (midi que não está na janela) não pontua ----
before = g.score
g.process_onset(midi=999, ts=time.time())
assert g.score == before, "midi inexistente não devia pontuar"
print("  ✓ ataque de nota inexistente ignorado\n")

# ---- Teste 3: miss ao passar da janela ----
target2 = g.notes[1]
# avança o relógio pra muito além do hit_time da 2ª nota
g.start_wall = time.time() - (target2.hit_time + 5.0) - __import__("game").COUNTDOWN
g._check_misses()
print(f"após passar do tempo: nota2 result={target2.result}")
assert target2.result == "miss", f"esperava miss, veio {target2.result}"
assert g.combo == 0, "miss deve zerar combo"
print("  ✓ nota não tocada vira miss e zera combo\n")

# ---- Teste 4: desenho não crasha ----
g.screen.fill((0, 0, 0))
g._draw_lanes()
g._draw_notes()
g._draw_flashes()
g._draw_hud()
g._draw_pitch()
g._draw_countdown()
print("  ✓ todos os _draw_* rodaram sem erro\n")

# ---- Teste 5: mock play acerta a nota mais próxima ----
g._reset()
nxt = min((n for n in g.notes if not n.judged), key=lambda n: n.hit_time)
g.start_wall = time.time() - (nxt.hit_time) - __import__("game").COUNTDOWN
g._mock_play()
judged = [n for n in g.notes if n.judged]
print(f"  mock_play julgou {len(judged)} nota(s): {[n.result for n in judged]}")
assert len(judged) == 1 and judged[0].result in ("perfect", "good")
print("  ✓ ESPAÇO (mock) acerta a nota alvo\n")

import pygame
pygame.quit()
print("✅ Smoke test do jogo passou.")
