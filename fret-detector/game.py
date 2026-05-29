"""🎸 Guitar Hero com guitarra real.

Notas caem em 6 lanes (uma por corda). Quando uma nota cruza a linha de acerto,
toque-a na guitarra: o áudio é identificado e o acerto é julgado por timing.
Valida a NOTA (pitch); a corda/casa é só dica visual.

A lógica de jogo vive na classe GameScreen (usada tanto por este script quanto
pelo app integrado studio.py). Standalone:

    python game.py --device 2 --gain 40 --chart escala_mi
    python game.py --mock                      # ESPAÇO = tocar (sem guitarra)
    python game.py --list

Controles: ESPAÇO (mock) toca a nota · P pausa · R reinicia · ESC volta/sai
"""
import argparse
import os
import sys
import time
import warnings
from dataclasses import dataclass

warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

import ui
from fret_detector import TUNINGS, midi_to_note, fret_positions, find_tank_g_device
from charts import CHARTS, DEFAULT_CHART

# ---- layout ----
WIDTH, HEIGHT = 900, 660
N_LANES = 6
HIT_LINE_Y = HEIGHT - 120
NOTE_H = 34
NOTE_W_PAD = 14
LEAD_TIME = 2.0
COUNTDOWN = LEAD_TIME + 1.0
FPS = 60

# ---- julgamento (janelas em ms) — "normal" ----
PERFECT_MS = 70
GOOD_MS = 150

DIFFICULTY = {
    "easy":   {"lead_time": 2.8, "perfect_ms": 90, "good_ms": 190},
    "normal": {"lead_time": LEAD_TIME, "perfect_ms": PERFECT_MS, "good_ms": GOOD_MS},
    "hard":   {"lead_time": 1.3, "perfect_ms": 55, "good_ms": 110},
}

LANE_BG = (28, 28, 34)
LANE_BG_ALT = (33, 33, 40)
HIT_LINE = (90, 90, 110)
STRING_LABEL = {6: "6ª(E)", 5: "5ª(A)", 4: "4ª(D)", 3: "3ª(G)", 2: "2ª(B)", 1: "1ª(e)"}


def judge(delta_ms: float, perfect_ms: float = PERFECT_MS, good_ms: float = GOOD_MS) -> str | None:
    a = abs(delta_ms)
    if a <= perfect_ms:
        return "perfect"
    if a <= good_ms:
        return "good"
    return None


def suggest_position(midi: int, tuning: list[str]) -> tuple[int, int] | None:
    pos = fret_positions(midi, tuning)
    if not pos:
        return None
    return min(pos, key=lambda sf: (sf[1], sf[0]))


@dataclass
class GameNote:
    midi: int
    hit_time: float
    lane: int
    string_num: int
    fret: int
    name: str
    judged: bool = False
    result: str | None = None


def build_notes(chart, tuning_name: str) -> list[GameNote]:
    tuning = TUNINGS[tuning_name]
    spb = 60.0 / chart.bpm
    out = []
    for n in chart.notes:
        pos = suggest_position(n.midi, tuning)
        string_num, fret = pos if pos else (1, 0)
        out.append(GameNote(
            midi=n.midi, hit_time=n.beat * spb, lane=6 - string_num,
            string_num=string_num, fret=fret, name=midi_to_note(n.midi),
        ))
    return out


class GameScreen:
    """Tela do jogo — NÃO cria display; desenha no surface recebido em draw().
    Reusada pelo standalone (game.py) e pelo app integrado (studio.py)."""

    def __init__(self, chart, tuning_name, engine=None, audio_offset=0.0,
                 show_hint=True, mock=False, difficulty="normal"):
        pygame.font.init()
        self.chart = chart
        self.tuning_name = tuning_name
        self.engine = engine
        self.audio_offset = audio_offset
        self.show_hint = show_hint
        self.mock = mock

        diff = DIFFICULTY[difficulty]
        self.difficulty = difficulty
        self.lead_time = diff["lead_time"]
        self.perfect_ms = diff["perfect_ms"]
        self.good_ms = diff["good_ms"]
        self.countdown = self.lead_time + 1.0

        self.font_note = ui.font(20, bold=True)
        self.font_hint = ui.font(13)
        self.font_hud = ui.font(22, bold=True)
        self.font_big = ui.font(54, bold=True)
        self.font_sm = ui.font(15)
        self.lane_w = WIDTH / N_LANES
        self._reset()

    def _reset(self):
        self.notes = build_notes(self.chart, self.tuning_name)
        self.start_wall = time.time()
        self.paused = False
        self.pause_accum = 0.0
        self._pause_mark = 0.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.counts = {"perfect": 0, "good": 0, "miss": 0}
        self.flashes = []
        self.finished_at = None

    # ---- tempo ----
    def elapsed(self) -> float:
        return (time.time() - self.start_wall) - self.countdown - self.pause_accum

    def song_done(self) -> bool:
        return self.notes != [] and all(n.judged for n in self.notes)

    # ---- julgamento ----
    def process_onset(self, midi: int, ts: float):
        onset_elapsed = (ts - self.start_wall) - self.countdown - self.pause_accum - self.audio_offset
        best, best_dt = None, None
        for n in self.notes:
            if n.judged or n.midi != midi:
                continue
            dt = abs(n.hit_time - onset_elapsed)
            if best is None or dt < best_dt:
                best, best_dt = n, dt
        if best is None:
            return
        res = judge((onset_elapsed - best.hit_time) * 1000, self.perfect_ms, self.good_ms)
        if res:
            best.judged = True
            best.result = res
            self._register(res, best.lane)

    def _register(self, result: str, lane: int):
        self.counts[result] += 1
        if result == "perfect":
            self.score += 100; self.combo += 1
        elif result == "good":
            self.score += 50; self.combo += 1
        else:
            self.combo = 0
        self.max_combo = max(self.max_combo, self.combo)
        self.flashes.append([lane, result, time.time() + 0.35])

    def _check_misses(self):
        el = self.elapsed()
        for n in self.notes:
            if not n.judged and (el - n.hit_time) > self.good_ms / 1000:
                n.judged = True
                n.result = "miss"
                self._register("miss", n.lane)

    def _mock_play(self):
        cand = [n for n in self.notes if not n.judged]
        if not cand:
            return
        el = self.elapsed()
        n = min(cand, key=lambda nn: abs(nn.hit_time - el))
        self.process_onset(n.midi, time.time())

    # ---- entrada / atualização ----
    def handle_event(self, ev) -> str | None:
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                return "back"
            if ev.key == pygame.K_r:
                self._reset()
            elif ev.key == pygame.K_p:
                self.paused = not self.paused
                if self.paused:
                    self._pause_mark = time.time()
                else:
                    self.pause_accum += time.time() - self._pause_mark
            elif ev.key == pygame.K_SPACE and self.mock and not self.paused:
                self._mock_play()
        return None

    def update(self):
        if self.paused:
            return
        if self.engine is not None:
            onset = self.engine.poll_onset()
            if onset is not None and self.elapsed() > -0.5:
                self.process_onset(onset[0], onset[1])
        self._check_misses()
        if self.song_done() and self.finished_at is None:
            self.finished_at = time.time()

    # ---- desenho ----
    def _lane_x(self, lane: int) -> float:
        return lane * self.lane_w

    def _draw_lanes(self, surf):
        for lane in range(N_LANES):
            x = self._lane_x(lane)
            color = LANE_BG if lane % 2 == 0 else LANE_BG_ALT
            pygame.draw.rect(surf, color, (x, 0, self.lane_w, HEIGHT))
            sn = 6 - lane
            ui.draw_text(surf, STRING_LABEL[sn], self.font_sm, ui.DIM,
                         center=(x + self.lane_w / 2, HEIGHT - 18))
        pygame.draw.line(surf, HIT_LINE, (0, HIT_LINE_Y), (WIDTH, HIT_LINE_Y), 3)
        for lane in range(N_LANES):
            cx = self._lane_x(lane) + self.lane_w / 2
            pygame.draw.circle(surf, ui.LANE_COLORS[lane], (int(cx), HIT_LINE_Y), 22, 3)

    def _draw_notes(self, surf):
        el = self.elapsed()
        for n in self.notes:
            if n.judged:
                continue
            progress = (el - (n.hit_time - self.lead_time)) / self.lead_time
            if progress < -0.05 or progress > 1.25:
                continue
            y = progress * HIT_LINE_Y
            x = self._lane_x(n.lane) + NOTE_W_PAD / 2
            w = self.lane_w - NOTE_W_PAD
            rect = pygame.Rect(int(x), int(y - NOTE_H / 2), int(w), NOTE_H)
            pygame.draw.rect(surf, ui.LANE_COLORS[n.lane], rect, border_radius=8)
            ui.draw_text(surf, n.name, self.font_note, (10, 10, 10), center=rect.center)
            if self.show_hint:
                hint = "solta" if n.fret == 0 else f"casa {n.fret}"
                ui.draw_text(surf, hint, self.font_hint, ui.FG,
                             midtop=(rect.centerx, rect.bottom + 2))

    def _draw_flashes(self, surf):
        now = time.time()
        self.flashes = [f for f in self.flashes if f[2] > now]
        for lane, result, _ in self.flashes:
            cx = self._lane_x(lane) + self.lane_w / 2
            col = {"perfect": ui.GREEN, "good": ui.YELLOW, "miss": ui.RED}[result]
            ui.draw_text(surf, result.upper(), self.font_sm, col,
                         center=(cx, HIT_LINE_Y - 48))
            if result != "miss":
                pygame.draw.circle(surf, col, (int(cx), HIT_LINE_Y), 26, 5)

    def _draw_hud(self, surf):
        ui.draw_text(surf, f"Score {self.score}", self.font_hud, ui.FG, topleft=(16, 12))
        ui.draw_text(surf, f"Combo {self.combo}", self.font_hud,
                     ui.GREEN if self.combo >= 5 else ui.FG, topleft=(16, 40))
        total = sum(self.counts.values())
        hits = self.counts["perfect"] + self.counts["good"]
        acc = (hits / total * 100) if total else 100.0
        ui.draw_text(surf, f"{acc:5.1f}%", self.font_hud, ui.FG, topleft=(WIDTH - 110, 12))
        c = self.counts
        ui.draw_text(surf, f"P {c['perfect']} G {c['good']} Miss {c['miss']}",
                     self.font_sm, ui.DIM, topleft=(WIDTH - 180, 44))

    def _draw_status(self, surf):
        if self.engine is None:
            ui.draw_text(surf, "MOCK — ESPAÇO toca a nota alvo", self.font_sm, ui.YELLOW,
                         midtop=(WIDTH / 2, 14))
        else:
            midi, freq = self.engine.current_pitch()
            if midi is not None:
                ui.draw_text(surf, f"ouvindo: {midi_to_note(midi)} ({freq:.1f} Hz)",
                             self.font_sm, ui.DIM, midtop=(WIDTH / 2, 14))

    def _draw_countdown(self, surf):
        el = self.elapsed()
        if el >= 0:
            return
        n = int(-el) + 1
        txt = str(n) if n <= int(self.countdown) else "GO"
        ui.draw_text(surf, txt, self.font_big, ui.FG, center=(WIDTH / 2, HEIGHT / 2 - 20))

    def _draw_results(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))
        c = self.counts
        total = sum(c.values()) or 1
        acc = (c["perfect"] + c["good"]) / total * 100
        lines = [
            ("FIM!", self.font_big, ui.FG),
            (f"Score: {self.score}", self.font_hud, ui.FG),
            (f"Precisão: {acc:.1f}%   Combo máx: {self.max_combo}", self.font_hud, ui.FG),
            (f"Perfect {c['perfect']}   Good {c['good']}   Miss {c['miss']}", self.font_sm, ui.DIM),
            ("R = de novo    ESC = voltar", self.font_sm, ui.YELLOW),
        ]
        y = HEIGHT / 2 - 120
        for text, fnt, col in lines:
            r = ui.draw_text(surf, text, fnt, col, center=(WIDTH / 2, y))
            y += r.height + 14

    def draw(self, surf):
        surf.fill(ui.BG)
        self._draw_lanes(surf)
        self._draw_notes(surf)
        self._draw_flashes(surf)
        self._draw_hud(surf)
        self._draw_status(surf)
        self._draw_countdown(surf)
        if self.paused:
            ui.draw_text(surf, "PAUSA", self.font_big, ui.FG, center=(WIDTH / 2, HEIGHT / 2 - 20))
        if self.song_done():
            self._draw_results(surf)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", type=int)
    parser.add_argument("--gain", type=float, default=40.0)
    parser.add_argument("--chart", default=DEFAULT_CHART, choices=list(CHARTS.keys()))
    parser.add_argument("--difficulty", default="normal", choices=list(DIFFICULTY.keys()))
    parser.add_argument("--audio-offset-ms", type=float, default=80.0)
    parser.add_argument("--no-hint", action="store_true")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("Músicas disponíveis:")
        for key, ch in CHARTS.items():
            print(f"  {key:<14} — {ch.name} ({ch.bpm} BPM, {len(ch.notes)} notas, {ch.tuning})")
        return

    chart = CHARTS[args.chart]
    engine = None
    audio_offset = 0.0
    if not args.mock:
        from audio_engine import AudioEngine
        import sounddevice as sd
        device = args.device if args.device is not None else find_tank_g_device()
        if device is None:
            print("⚠️  TANK-G não encontrado. Use --device N (list_devices.py) ou --mock.")
            sys.exit(1)
        engine = AudioEngine(device=device, gain=args.gain)
        try:
            engine.start()
        except sd.PortAudioError as e:
            print(f"\n❌ Não consegui abrir o áudio no device {device}: {e}")
            print("   Feche o M-EFCS/outras janelas, tente --device 27 (WASAPI) ou --mock.")
            sys.exit(1)
        audio_offset = args.audio_offset_ms / 1000.0
        print(f"🎸 Capturando de [{device}] {engine.device_name()} | gain {args.gain}x")

    print(f"🎮 {chart.name} — {chart.bpm} BPM ({chart.tuning}) | dificuldade: {args.difficulty}")
    if args.mock:
        print("   MODO MOCK: ESPAÇO no tempo certo pra 'tocar' a nota.")

    pygame.display.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"TANK-G-NOTA — {chart.name}")
    clock = pygame.time.Clock()
    gs = GameScreen(chart, chart.tuning, engine=engine, audio_offset=audio_offset,
                    show_hint=not args.no_hint, mock=args.mock, difficulty=args.difficulty)
    try:
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif gs.handle_event(ev) == "back":
                    running = False
            gs.update()
            gs.draw(screen)
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()
    finally:
        if engine is not None:
            engine.stop()


if __name__ == "__main__":
    main()
