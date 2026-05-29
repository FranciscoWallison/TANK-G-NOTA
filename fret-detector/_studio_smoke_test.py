"""Smoke test do TANK-G Studio SEM display/áudio real (SDL dummy).
Cria o app, navega entre as 4 telas + jogo, desenha cada uma sem crashar.
Força engine=None (sem hardware)."""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pygame
import studio
from studio import App, AppState

print("===== STUDIO SMOKE TEST (headless) =====\n")

# Evita abrir áudio real: força _make_engine a devolver None
App._make_engine = lambda self: None
# Não persistir settings durante o teste
AppState.save = lambda self: None

state = AppState()
app = App(state)
print("App criado (engine=None)")

surf = app.surface
for name in ("menu", "device", "tuner", "train", "game"):
    app.go(name)
    app.screen.update()
    app.screen.draw(surf)
    print(f"  ✓ tela '{name}' navegou, atualizou e desenhou")

# volta ao menu e simula clique de toggle de dificuldade/monitor
app.go("menu")
m = app.screen
m._cycle_diff()
print(f"  ✓ ciclo de dificuldade → {app.state.difficulty}")
m._toggle_monitor()   # engine None: toggle só altera estado
print(f"  ✓ toggle monitor → {app.state.monitor_on}")

pygame.quit()
print("\n✅ Smoke test do studio passou.")
