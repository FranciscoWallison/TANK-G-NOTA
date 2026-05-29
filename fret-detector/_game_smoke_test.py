"""Smoke test do jogo SEM display real (SDL dummy). Valida que:
  - GameScreen inicializa headless
  - process_onset no tempo certo marca 'perfect' e pontua
  - nota que passa vira 'miss'
  - draw(surface) roda sem crashar
  - mock_play acerta a nota alvo
"""
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pygame
pygame.display.init()
pygame.display.set_mode((900, 660))   # garante contexto p/ fontes
pygame.font.init()

from game import GameScreen, WIDTH, HEIGHT
from charts import CHARTS

print("===== GAME SMOKE TEST (headless) =====\n")

chart = CHARTS["escala_mi"]
g = GameScreen(chart, chart.tuning, engine=None, audio_offset=0.0, show_hint=True, mock=True)
surf = pygame.Surface((WIDTH, HEIGHT))
print(f"init OK — {len(g.notes)} notas, lane da 1ª = {g.notes[0].lane}")

# ---- Teste 1: acerto perfeito ----
target = g.notes[0]
g.start_wall = time.time() - (target.hit_time + g.pause_accum) - g.countdown
g.process_onset(target.midi, time.time())
print(f"após onset no tempo certo: result={target.result} score={g.score} combo={g.combo}")
assert target.result == "perfect", f"esperava perfect, veio {target.result}"
assert g.score == 100 and g.combo == 1
print("  ✓ acerto perfeito pontua\n")

# ---- Teste 2: nota inexistente não pontua ----
before = g.score
g.process_onset(midi=999, ts=time.time())
assert g.score == before
print("  ✓ ataque de nota inexistente ignorado\n")

# ---- Teste 3: miss ao passar da janela ----
target2 = g.notes[1]
g.start_wall = time.time() - (target2.hit_time + 5.0) - g.countdown
g._check_misses()
print(f"após passar do tempo: nota2 result={target2.result}")
assert target2.result == "miss"
assert g.combo == 0
print("  ✓ nota não tocada vira miss e zera combo\n")

# ---- Teste 4: draw não crasha ----
g.draw(surf)
print("  ✓ draw(surface) rodou sem erro\n")

# ---- Teste 5: mock play acerta a nota mais próxima ----
g._reset()
nxt = min((n for n in g.notes if not n.judged), key=lambda n: n.hit_time)
g.start_wall = time.time() - nxt.hit_time - g.countdown
g._mock_play()
judged = [n for n in g.notes if n.judged]
print(f"  mock_play julgou {len(judged)} nota(s): {[n.result for n in judged]}")
assert len(judged) == 1 and judged[0].result in ("perfect", "good")
print("  ✓ ESPAÇO (mock) acerta a nota alvo\n")

pygame.quit()
print("✅ Smoke test do jogo passou.")
