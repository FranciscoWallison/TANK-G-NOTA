"""🎸 TANK-G Studio — app unificado.

Uma janela com tudo: identifica o TANK-G, afinador, treino (validar nota tocada),
controle de velocidade, monitor pelo fone (o app reproduz a guitarra) — e daí
joga uma música. Reúne tuner/detector/jogo num só programa.

    python studio.py [--device N] [--gain 40]

Navegação: clique nos botões · ESC volta ao menu (no menu, ESC sai).
"""
import argparse
import json
import os
import sys
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path

warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

import ui
from fret_detector import find_tank_g_device, TUNINGS
from charts import CHARTS, DEFAULT_CHART
from game import GameScreen, WIDTH, HEIGHT, FPS
from screens import MenuScreen, DeviceScreen, TunerScreen, TrainScreen

SCRIPT_DIR = Path(__file__).resolve().parent
SETTINGS = SCRIPT_DIR / "settings.json"


@dataclass
class AppState:
    device_in: int | None = None
    device_out: int | None = None
    gain: float = 40.0
    tuning: str = "standard"
    difficulty: str = "normal"
    monitor_on: bool = False
    monitor_gain: float = 12.0
    chart: str = DEFAULT_CHART
    validation: str = "note+open"   # "note" | "note+open" | "note+fret"

    @classmethod
    def load(cls):
        st = cls()
        if SETTINGS.exists():
            try:
                data = json.loads(SETTINGS.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if hasattr(st, k):
                        setattr(st, k, v)
            except Exception:
                pass
        if st.tuning not in TUNINGS:
            st.tuning = "standard"
        if st.chart not in CHARTS:
            st.chart = DEFAULT_CHART
        return st

    def save(self):
        try:
            SETTINGS.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except Exception:
            pass


class App:
    def __init__(self, state: AppState):
        self.state = state
        self.width, self.height = WIDTH, HEIGHT
        pygame.display.init()
        pygame.font.init()
        self.surface = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("TANK-G Studio")
        self.clock = pygame.time.Clock()

        self.engine = self._make_engine()
        self.current_name = "menu"
        self.screen = MenuScreen(self)

    def _make_engine(self):
        from audio_engine import AudioEngine
        import sounddevice as sd
        dev = self.state.device_in if self.state.device_in is not None else find_tank_g_device()
        if dev is None:
            print("⚠️  Nenhuma entrada de áudio encontrada. Telas vão mostrar '—'.")
            return None
        self.state.device_in = dev
        eng = AudioEngine(device=dev, gain=self.state.gain,
                          output_device=self.state.device_out,
                          monitor_on=self.state.monitor_on,
                          monitor_gain=self.state.monitor_gain)
        try:
            eng.start()
            print(f"🎸 Áudio: [{dev}] {eng.device_name()} | gain {self.state.gain}x"
                  f" | monitor {'ON' if eng.monitor_on else 'OFF'}")
        except sd.PortAudioError as e:
            print(f"⚠️  Não consegui abrir o áudio: {e}")
            print("   Feche o M-EFCS/outras janelas; troque a entrada em 'Dispositivo'.")
            return None
        return eng

    def go(self, name: str):
        self.current_name = name
        if name == "menu":
            self.screen = MenuScreen(self)
        elif name == "device":
            self.screen = DeviceScreen(self)
        elif name == "tuner":
            self.screen = TunerScreen(self)
        elif name == "train":
            self.screen = TrainScreen(self)
        elif name == "game":
            chart = CHARTS[self.state.chart]
            self.screen = GameScreen(
                chart, chart.tuning, engine=self.engine,
                audio_offset=0.08, show_hint=True, mock=(self.engine is None),
                difficulty=self.state.difficulty,
                validate_open=(self.state.validation == "note+open"),
            )

    def run(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                    break
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    if self.current_name == "menu":
                        running = False
                    else:
                        self.go("menu")
                    continue
                res = self.screen.handle_event(ev)
                if res == "back":
                    self.go("menu")
                elif res == "quit":
                    running = False
            self.screen.update()
            self.screen.draw(self.surface)
            pygame.display.flip()
            self.clock.tick(FPS)
        if self.engine is not None:
            self.engine.stop()
        self.state.save()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", type=int, help="ID da entrada (sobrescreve o salvo)")
    parser.add_argument("--gain", type=float, help="ganho de análise (sobrescreve o salvo)")
    args = parser.parse_args()

    state = AppState.load()
    if args.device is not None:
        state.device_in = args.device
    if args.gain is not None:
        state.gain = args.gain

    App(state).run()


if __name__ == "__main__":
    main()
