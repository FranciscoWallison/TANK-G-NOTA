"""🎸 Guitar Hero com guitarra real — protótipo.

Notas caem em 6 lanes (uma por corda). Quando uma nota cruza a linha de acerto,
toque-a na guitarra: o áudio é identificado e o acerto é julgado por timing.
Valida a NOTA (pitch); a corda/casa é só dica visual.

Uso:
    python game.py --device 2 --gain 40 --chart escala_mi
    python game.py --mock                      # testar sem guitarra (ESPAÇO = tocar)
    python game.py --list                      # lista as músicas

Controles: ESPAÇO (mock) toca a nota alvo · P pausa · R reinicia · ESC sai
"""
import argparse
import sys
import time
from dataclasses import dataclass

import pygame

from fret_detector import TUNINGS, midi_to_note, fret_positions, find_tank_g_device
from charts import CHARTS, DEFAULT_CHART

# ---- layout ----
WIDTH, HEIGHT = 900, 660
N_LANES = 6
HIT_LINE_Y = HEIGHT - 120
NOTE_H = 34
NOTE_W_PAD = 14
LEAD_TIME = 2.0          # s que a nota leva pra cair do topo até a linha
COUNTDOWN = LEAD_TIME + 1.0
FPS = 60

# ---- julgamento (janelas em ms) ----
PERFECT_MS = 70
GOOD_MS = 150

# ---- cores ----
BG = (18, 18, 22)
FG = (240, 240, 240)
DIM = (120, 120, 130)
LANE_BG = (28, 28, 34)
LANE_BG_ALT = (33, 33, 40)
HIT_LINE = (90, 90, 110)
PERFECT_COL = (76, 200, 120)
GOOD_COL = (255, 193, 7)
MISS_COL = (244, 67, 54)
# cor por lane (corda 6→1 = lane 0→5)
LANE_COLORS = [
    (231, 76, 60),    # corda 6 (E grave)
    (230, 126, 34),   # corda 5 (A)
    (241, 196, 15),   # corda 4 (D)
    (46, 204, 113),   # corda 3 (G)
    (52, 152, 219),   # corda 2 (B)
    (155, 89, 182),   # corda 1 (E agudo)
]
STRING_LABEL = {6: "6ª(E)", 5: "5ª(A)", 4: "4ª(D)", 3: "3ª(G)", 2: "2ª(B)", 1: "1ª(e)"}


def judge(delta_ms: float) -> str | None:
    """Classifica o acerto pelo erro de timing (ms). None = fora da janela (miss)."""
    a = abs(delta_ms)
    if a <= PERFECT_MS:
        return "perfect"
    if a <= GOOD_MS:
        return "good"
    return None


def suggest_position(midi: int, tuning: list[str]) -> tuple[int, int] | None:
    """Posição sugerida pra tocar a nota: menor casa (mais ergonômica)."""
    pos = fret_positions(midi, tuning)
    if not pos:
        return None
    # menor casa; desempate: corda mais aguda (string menor)
    return min(pos, key=lambda sf: (sf[1], sf[0]))


@dataclass
class GameNote:
    midi: int
    hit_time: float       # s desde o início da música
    lane: int             # 0..5
    string_num: int       # 1..6
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


class Game:
    def __init__(self, chart, tuning_name, engine=None, audio_offset=0.0,
                 show_hint=True, mock=False):
        self.chart = chart
        self.tuning_name = tuning_name
        self.engine = engine
        self.audio_offset = audio_offset
        self.show_hint = show_hint
        self.mock = mock

        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(f"TANK-G-NOTA — {chart.name}")
        self.clock = pygame.time.Clock()
        self.font_note = self._font(20, bold=True)
        self.font_hint = self._font(13)
        self.font_hud = self._font(22, bold=True)
        self.font_big = self._font(54, bold=True)
        self.font_sm = self._font(15)

        self.lane_w = WIDTH / N_LANES
        self._reset()

    def _font(self, size, bold=False):
        for name in ("Consolas", "DejaVu Sans Mono", "Courier New"):
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                continue
        return pygame.font.Font(None, size)

    def _reset(self):
        self.notes = build_notes(self.chart, self.tuning_name)
        self.start_wall = time.time()
        self.paused = False
        self.pause_accum = 0.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.counts = {"perfect": 0, "good": 0, "miss": 0}
        self.flashes = []   # (lane, result, t_expire)
        self.last_pitch_midi = None

    # ---- tempo ----
    def elapsed(self) -> float:
        return (time.time() - self.start_wall) - COUNTDOWN - self.pause_accum

    def song_done(self) -> bool:
        return all(n.judged for n in self.notes) and self.notes != []

    # ---- julgamento de um ataque ----
    def process_onset(self, midi: int, ts: float):
        onset_elapsed = (ts - self.start_wall) - COUNTDOWN - self.pause_accum - self.audio_offset
        best, best_dt = None, None
        for n in self.notes:
            if n.judged or n.midi != midi:
                continue
            dt = abs(n.hit_time - onset_elapsed)
            if best is None or dt < best_dt:
                best, best_dt = n, dt
        if best is None:
            return
        res = judge((onset_elapsed - best.hit_time) * 1000)
        if res:
            best.judged = True
            best.result = res
            self._register(res, best.lane)

    def _register(self, result: str, lane: int):
        self.counts[result] += 1
        if result == "perfect":
            self.score += 100
            self.combo += 1
        elif result == "good":
            self.score += 50
            self.combo += 1
        else:
            self.combo = 0
        self.max_combo = max(self.max_combo, self.combo)
        self.flashes.append([lane, result, time.time() + 0.35])

    def _check_misses(self):
        el = self.elapsed()
        for n in self.notes:
            if not n.judged and (el - n.hit_time) > GOOD_MS / 1000:
                n.judged = True
                n.result = "miss"
                self._register("miss", n.lane)

    def _mock_play(self):
        """ESPAÇO no modo mock: toca a nota não-julgada mais próxima da linha."""
        cand = [n for n in self.notes if not n.judged]
        if not cand:
            return
        el = self.elapsed()
        n = min(cand, key=lambda nn: abs(nn.hit_time - el))
        self.process_onset(n.midi, time.time())

    # ---- desenho ----
    def _lane_x(self, lane: int) -> float:
        return lane * self.lane_w

    def _draw_lanes(self):
        for lane in range(N_LANES):
            x = self._lane_x(lane)
            color = LANE_BG if lane % 2 == 0 else LANE_BG_ALT
            pygame.draw.rect(self.screen, color, (x, 0, self.lane_w, HEIGHT))
            # rótulo da corda no rodapé
            sn = 6 - lane
            lbl = self.font_sm.render(STRING_LABEL[sn], True, DIM)
            self.screen.blit(lbl, (x + self.lane_w / 2 - lbl.get_width() / 2, HEIGHT - 28))
        # linha de acerto
        pygame.draw.line(self.screen, HIT_LINE, (0, HIT_LINE_Y), (WIDTH, HIT_LINE_Y), 3)
        for lane in range(N_LANES):
            cx = self._lane_x(lane) + self.lane_w / 2
            pygame.draw.circle(self.screen, LANE_COLORS[lane], (int(cx), HIT_LINE_Y), 22, 3)

    def _draw_notes(self):
        el = self.elapsed()
        for n in self.notes:
            if n.judged:
                continue
            # progress: 0 no topo (hit_time - LEAD_TIME), 1 na linha (hit_time)
            progress = (el - (n.hit_time - LEAD_TIME)) / LEAD_TIME
            if progress < -0.05 or progress > 1.25:
                continue
            y = progress * HIT_LINE_Y
            x = self._lane_x(n.lane) + NOTE_W_PAD / 2
            w = self.lane_w - NOTE_W_PAD
            rect = pygame.Rect(int(x), int(y - NOTE_H / 2), int(w), NOTE_H)
            pygame.draw.rect(self.screen, LANE_COLORS[n.lane], rect, border_radius=8)
            # nome da nota
            txt = self.font_note.render(n.name, True, (10, 10, 10))
            self.screen.blit(txt, (rect.centerx - txt.get_width() / 2,
                                   rect.centery - txt.get_height() / 2))
            # dica de casa
            if self.show_hint:
                hint = "solta" if n.fret == 0 else f"casa {n.fret}"
                h = self.font_hint.render(hint, True, FG)
                self.screen.blit(h, (rect.centerx - h.get_width() / 2, rect.bottom + 2))

    def _draw_flashes(self):
        now = time.time()
        self.flashes = [f for f in self.flashes if f[2] > now]
        for lane, result, _ in self.flashes:
            cx = self._lane_x(lane) + self.lane_w / 2
            col = {"perfect": PERFECT_COL, "good": GOOD_COL, "miss": MISS_COL}[result]
            label = self.font_sm.render(result.upper(), True, col)
            self.screen.blit(label, (cx - label.get_width() / 2, HIT_LINE_Y - 48))
            if result != "miss":
                pygame.draw.circle(self.screen, col, (int(cx), HIT_LINE_Y), 26, 5)

    def _draw_hud(self):
        score = self.font_hud.render(f"Score {self.score}", True, FG)
        self.screen.blit(score, (16, 12))
        combo = self.font_hud.render(f"Combo {self.combo}", True,
                                     PERFECT_COL if self.combo >= 5 else FG)
        self.screen.blit(combo, (16, 40))
        total = sum(self.counts.values())
        hits = self.counts["perfect"] + self.counts["good"]
        acc = (hits / total * 100) if total else 100.0
        accs = self.font_hud.render(f"{acc:5.1f}%", True, FG)
        self.screen.blit(accs, (WIDTH - accs.get_width() - 16, 12))
        c = self.counts
        cnt = self.font_sm.render(
            f"P {c['perfect']}  G {c['good']}  Miss {c['miss']}", True, DIM)
        self.screen.blit(cnt, (WIDTH - cnt.get_width() - 16, 42))

    def _draw_countdown(self):
        el = self.elapsed()
        if el >= 0:
            return
        n = int(-el) + 1
        txt = self.font_big.render(str(n) if n <= int(COUNTDOWN) else "GO", True, FG)
        self.screen.blit(txt, (WIDTH / 2 - txt.get_width() / 2, HEIGHT / 2 - 40))

    def _draw_pitch(self):
        if self.engine is None:
            mode = self.font_sm.render("MOCK — ESPAÇO toca a nota alvo", True, GOOD_COL)
            self.screen.blit(mode, (WIDTH / 2 - mode.get_width() / 2, 14))
            return
        midi, freq = self.engine.current_pitch()
        if midi is not None:
            t = self.font_sm.render(f"ouvindo: {midi_to_note(midi)} ({freq:.1f} Hz)", True, DIM)
            self.screen.blit(t, (WIDTH / 2 - t.get_width() / 2, 14))

    def _draw_results(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        c = self.counts
        total = sum(c.values()) or 1
        acc = (c["perfect"] + c["good"]) / total * 100
        lines = [
            ("FIM!", self.font_big, FG),
            (f"Score: {self.score}", self.font_hud, FG),
            (f"Precisão: {acc:.1f}%   Combo máx: {self.max_combo}", self.font_hud, FG),
            (f"Perfect {c['perfect']}   Good {c['good']}   Miss {c['miss']}", self.font_sm, DIM),
            ("R = de novo    ESC = sair", self.font_sm, GOOD_COL),
        ]
        y = HEIGHT / 2 - 120
        for text, font, col in lines:
            s = font.render(text, True, col)
            self.screen.blit(s, (WIDTH / 2 - s.get_width() / 2, y))
            y += s.get_height() + 14

    # ---- loop principal ----
    def run(self):
        running = True
        finished_at = None
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                    elif ev.key == pygame.K_r:
                        self._reset()
                        finished_at = None
                    elif ev.key == pygame.K_p:
                        self.paused = not self.paused
                        self._pause_mark = time.time()
                    elif ev.key == pygame.K_SPACE and self.mock and not self.paused:
                        self._mock_play()

            if not self.paused:
                # consome ataque real do áudio
                if self.engine is not None:
                    onset = self.engine.poll_onset()
                    if onset is not None and self.elapsed() > -0.5:
                        self.process_onset(onset[0], onset[1])
                self._check_misses()

            # desenho
            self.screen.fill(BG)
            self._draw_lanes()
            self._draw_notes()
            self._draw_flashes()
            self._draw_hud()
            self._draw_pitch()
            self._draw_countdown()

            if self.paused:
                p = self.font_big.render("PAUSA", True, FG)
                self.screen.blit(p, (WIDTH / 2 - p.get_width() / 2, HEIGHT / 2 - 40))

            if self.song_done():
                if finished_at is None:
                    finished_at = time.time()
                self._draw_results()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", type=int, help="ID do dispositivo de entrada")
    parser.add_argument("--gain", type=float, default=40.0)
    parser.add_argument("--chart", default=DEFAULT_CHART, choices=list(CHARTS.keys()))
    parser.add_argument("--audio-offset-ms", type=float, default=80.0,
                        help="compensa latência do pipeline (default 80; ignore em --mock)")
    parser.add_argument("--no-hint", action="store_true", help="esconde a dica de casa")
    parser.add_argument("--mock", action="store_true",
                        help="sem guitarra: ESPAÇO toca a nota alvo (testar o jogo)")
    parser.add_argument("--list", action="store_true", help="lista as músicas e sai")
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
            print("⚠️  TANK-G não encontrado. Use --device N (veja list_devices.py) ou --mock.")
            sys.exit(1)
        engine = AudioEngine(device=device, gain=args.gain)
        try:
            engine.start()
        except sd.PortAudioError as e:
            print(f"\n❌ Não consegui abrir o áudio no device {device}: {e}\n")
            print("Causas comuns:")
            print("  1. O app M-EFCS está aberto e segurando o USB — feche-o.")
            print("  2. Outra janela do jogo/afinador/detector ainda está rodando — feche-a.")
            print("  3. O índice do device mudou — rode:  python list_devices.py")
            print("  4. Tente outra API do mesmo dispositivo (ex.: WASAPI):  --device 27")
            print("  5. Pra testar sem guitarra:  --mock")
            sys.exit(1)
        audio_offset = args.audio_offset_ms / 1000.0
        print(f"🎸 Capturando de [{device}] {engine.device_name()} | gain {args.gain}x")

    print(f"🎮 {chart.name} — {chart.bpm} BPM ({chart.tuning})")
    if args.mock:
        print("   MODO MOCK: pressione ESPAÇO no tempo certo pra 'tocar' a nota.")

    try:
        game = Game(chart, chart.tuning, engine=engine, audio_offset=audio_offset,
                    show_hint=not args.no_hint, mock=args.mock)
        game.run()
    finally:
        if engine is not None:
            engine.stop()


if __name__ == "__main__":
    main()
