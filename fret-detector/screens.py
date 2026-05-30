"""Telas do TANK-G Studio: Menu (hub), Dispositivo, Afinador, Treino.

Cada tela recebe o `app` (studio) e expõe handle_event/update/draw(surf).
Navega via app.go("menu"|"device"|"tuner"|"train"|"game").
"""
import time
from collections import deque
from pathlib import Path
import numpy as np
import pygame
import sounddevice as sd

import ui
from fret_detector import (
    freq_to_midi, midi_to_note, note_to_midi, TUNINGS, find_tank_g_device,
)

SCRIPT_DIR = Path(__file__).resolve().parent

CENTS_GREEN = 5
CENTS_YELLOW = 15
CENTS_RANGE = 50


def color_for_cents(c):
    a = abs(c)
    if a <= CENTS_GREEN:
        return ui.GREEN
    if a <= CENTS_YELLOW:
        return ui.YELLOW
    return ui.RED


def draw_cents_bar(surf, cx, cy, half_w, cents):
    h = 12
    x0, x1 = cx - half_w, cx + half_w
    pygame.draw.rect(surf, ui.PANEL, (x0, cy - h // 2, 2 * half_w, h), border_radius=4)
    gh = int(CENTS_GREEN / CENTS_RANGE * half_w)
    yh = int(CENTS_YELLOW / CENTS_RANGE * half_w)
    pygame.draw.rect(surf, ui.RED, (x0, cy - h // 2, half_w - yh, h))
    pygame.draw.rect(surf, ui.RED, (cx + yh, cy - h // 2, half_w - yh, h))
    pygame.draw.rect(surf, ui.YELLOW, (cx - yh, cy - h // 2, yh - gh, h))
    pygame.draw.rect(surf, ui.YELLOW, (cx + gh, cy - h // 2, yh - gh, h))
    pygame.draw.rect(surf, ui.GREEN, (cx - gh, cy - h // 2, 2 * gh, h))
    c = max(-CENTS_RANGE, min(CENTS_RANGE, cents))
    nx = int(cx + c / CENTS_RANGE * half_w)
    col = color_for_cents(cents)
    pygame.draw.polygon(surf, col, [(nx - 9, cy - 26), (nx + 9, cy - 26), (nx, cy - 8)])
    pygame.draw.rect(surf, col, (nx - 2, cy - 8, 4, 16))


# ============================================================ MENU
class MenuScreen:
    def __init__(self, app):
        self.app = app
        W = app.width
        self.f_title = ui.font(44, bold=True)
        self.f = ui.font(20)
        self.f_sm = ui.font(15)
        bw, bh, gap = 320, 56, 16
        bx = W / 2 - bw / 2
        y0 = 250
        self.buttons = [
            ui.Button((bx, y0, bw, bh), "🎚  Dispositivo", lambda: app.go("device")),
            ui.Button((bx, y0 + (bh + gap), bw, bh), "🎯  Afinador", lambda: app.go("tuner")),
            ui.Button((bx, y0 + 2 * (bh + gap), bw, bh), "🎸  Treino (validar nota)", lambda: app.go("train")),
            ui.Button((bx, y0 + 3 * (bh + gap), bw, bh), "🎮  Jogar música", lambda: app.go("select"),
                      color=(40, 80, 60), hover=(55, 105, 80)),
        ]
        # toggles na base
        self.btn_monitor = ui.Button((bx, y0 + 4 * (bh + gap) + 10, 155, 46), "", self._toggle_monitor, fnt=self.f_sm)
        self.btn_diff = ui.Button((bx + 165, y0 + 4 * (bh + gap) + 10, 155, 46), "", self._cycle_diff, fnt=self.f_sm)
        # ferramenta de metrônomo (abaixo dos toggles)
        self.btn_metronome = ui.Button((bx, y0 + 4 * (bh + gap) + 68, bw, 40),
                                        "🎼  Metrônomo", lambda: app.go("metronome"), fnt=self.f_sm)

    def _toggle_monitor(self):
        st = self.app.state
        want = not st.monitor_on
        if self.app.engine is not None:
            self.app.engine.set_monitor(want, st.monitor_gain)
            # reflete o estado REAL (full-duplex pode falhar e voltar p/ OFF)
            st.monitor_on = self.app.engine.monitor_on
        else:
            st.monitor_on = want
        st.save()

    def _cycle_diff(self):
        order = ["easy", "normal", "hard"]
        st = self.app.state
        st.difficulty = order[(order.index(st.difficulty) + 1) % len(order)]
        st.save()

    def _adjust_vol(self, delta):
        st = self.app.state
        st.monitor_gain = max(1.0, min(40.0, round(st.monitor_gain + delta, 1)))
        if self.app.engine is not None:
            self.app.engine.monitor_gain = st.monitor_gain  # aplica ao vivo
        st.save()

    def handle_event(self, ev):
        for b in self.buttons:
            b.handle_event(ev)
        self.btn_monitor.handle_event(ev)
        self.btn_diff.handle_event(ev)
        self.btn_metronome.handle_event(ev)
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self._adjust_vol(+2)
            elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self._adjust_vol(-2)

    def update(self):
        pass

    def draw(self, surf):
        surf.fill(ui.BG)
        W = self.app.width
        ui.draw_text(surf, "TANK-G Studio", self.f_title, ui.FG, center=(W / 2, 70))
        ui.draw_text(surf, "afinar · validar · treinar · jogar", self.f_sm, ui.DIM, center=(W / 2, 110))

        # status do dispositivo + nível
        eng = self.app.engine
        name = eng.device_name() if eng else "—"
        dot = ui.GREEN if eng and eng.current_rms() > 0.01 else ui.DIM
        pygame.draw.circle(surf, dot, (int(W / 2 - 150), 165), 7)
        ui.draw_text(surf, f"Entrada: {name}", self.f_sm, ui.FG, midtop=(W / 2 + 5, 158))
        if eng:
            ui.level_bar(surf, (W / 2 - 150, 185, 300, 10), eng.current_rms())
        mon = "ON" if not eng else ("ON" if eng.monitor_on else "OFF")
        mon_avail = "" if (eng and eng.monitor_available) else "  (indisponível)"
        ui.draw_text(surf, f"Monitor (fone): {mon}{mon_avail}", self.f_sm, ui.DIM, midtop=(W / 2, 205))
        ui.draw_text(surf, f"Volume monitor: {self.app.state.monitor_gain:.0f}x   (+/− ajusta)",
                     self.f_sm, ui.DIM, midtop=(W / 2, 224))

        for b in self.buttons:
            b.draw(surf)
        self.btn_monitor.label = f"Monitor: {'ON' if self.app.state.monitor_on else 'OFF'}"
        self.btn_diff.label = f"Veloc.: {self.app.state.difficulty}"
        self.btn_monitor.draw(surf)
        self.btn_diff.draw(surf)
        self.btn_metronome.draw(surf)


# ============================================================ DISPOSITIVO
class DeviceScreen:
    def __init__(self, app):
        self.app = app
        self.f = ui.font(20)
        self.f_sm = ui.font(15)
        self.f_title = ui.font(30, bold=True)
        self._refresh_lists()
        W = app.width
        self.btn_in_prev = ui.Button((W / 2 - 230, 210, 40, 40), "‹", lambda: self._cycle("in", -1))
        self.btn_in_next = ui.Button((W / 2 + 190, 210, 40, 40), "›", lambda: self._cycle("in", +1))
        self.btn_out_prev = ui.Button((W / 2 - 230, 320, 40, 40), "‹", lambda: self._cycle("out", -1))
        self.btn_out_next = ui.Button((W / 2 + 190, 320, 40, 40), "›", lambda: self._cycle("out", +1))
        self.btn_auto = ui.Button((W / 2 - 110, 400, 220, 46), "Auto-detectar TANK-G", self._auto)
        self.btn_back = ui.Button((W / 2 - 110, 470, 220, 46), "‹ Voltar (ESC)", lambda: app.go("menu"))

    def _refresh_lists(self):
        devs = sd.query_devices()
        self.inputs = [(i, d["name"]) for i, d in enumerate(devs) if d["max_input_channels"] > 0]
        self.outputs = [(i, d["name"]) for i, d in enumerate(devs) if d["max_output_channels"] > 0]

    def _idx(self, lst, dev):
        for k, (i, _) in enumerate(lst):
            if i == dev:
                return k
        return 0

    def _cycle(self, which, step):
        eng = self.app.engine
        st = self.app.state
        if which == "in":
            k = (self._idx(self.inputs, st.device_in) + step) % len(self.inputs)
            st.device_in = self.inputs[k][0]
            self._safe(lambda: eng.set_input_device(st.device_in))
        else:
            k = (self._idx(self.outputs, st.device_out if st.device_out is not None else -1) + step) % len(self.outputs)
            st.device_out = self.outputs[k][0]
            self._safe(lambda: eng.set_output_device(st.device_out))
        st.save()

    def _auto(self):
        dev = find_tank_g_device()
        if dev is not None:
            self.app.state.device_in = dev
            self._safe(lambda: self.app.engine.set_input_device(dev))
            self.app.state.save()

    def _safe(self, fn):
        self.err = None
        try:
            fn()
        except Exception as e:
            self.err = str(e)[:70]

    err = None

    def handle_event(self, ev):
        for b in (self.btn_in_prev, self.btn_in_next, self.btn_out_prev,
                  self.btn_out_next, self.btn_auto, self.btn_back):
            b.handle_event(ev)

    def update(self):
        pass

    def draw(self, surf):
        surf.fill(ui.BG)
        W = self.app.width
        eng = self.app.engine
        st = self.app.state
        ui.draw_text(surf, "Dispositivo", self.f_title, ui.FG, center=(W / 2, 60))

        in_name = next((n for i, n in self.inputs if i == st.device_in), "—")
        is_tank = (find_tank_g_device() == st.device_in)
        ui.draw_text(surf, "Entrada (guitarra):", self.f_sm, ui.DIM, midtop=(W / 2, 175))
        col = ui.GREEN if is_tank else ui.FG
        ui.draw_text(surf, f"{in_name} (ID {st.device_in})", self.f, col, center=(W / 2, 230))
        if is_tank:
            ui.draw_text(surf, "✓ TANK-G", self.f_sm, ui.GREEN, midtop=(W / 2, 250))
        ui.level_bar(surf, (W / 2 - 150, 275, 300, 10), eng.current_rms() if eng else 0)

        out_name = next((n for i, n in self.outputs if i == st.device_out), "padrão do sistema")
        ui.draw_text(surf, "Saída (fone):", self.f_sm, ui.DIM, midtop=(W / 2, 290))
        ui.draw_text(surf, f"{out_name}", self.f, ui.FG, center=(W / 2, 340))

        for b in (self.btn_in_prev, self.btn_in_next, self.btn_out_prev,
                  self.btn_out_next, self.btn_auto, self.btn_back):
            b.draw(surf)
        if self.err:
            ui.draw_text(surf, f"erro: {self.err}", self.f_sm, ui.RED, midtop=(W / 2, 530))


# ============================================================ AFINADOR
class TunerScreen:
    def __init__(self, app):
        self.app = app
        self.f_big = ui.font(120, bold=True)
        self.f = ui.font(20)
        self.f_sm = ui.font(15)
        self.f_title = ui.font(26, bold=True)
        self._freqs = deque(maxlen=5)
        self._ema = None
        self.btn_back = ui.Button((20, app.height - 60, 160, 42), "‹ Voltar (ESC)", lambda: app.go("menu"), fnt=self.f_sm)

    def handle_event(self, ev):
        self.btn_back.handle_event(ev)

    def update(self):
        pass

    def draw(self, surf):
        surf.fill(ui.BG)
        W = self.app.width
        ui.draw_text(surf, "Afinador", self.f_title, ui.DIM, midtop=(W / 2, 20))
        midi, freq = self.app.engine.current_pitch() if self.app.engine else (None, 0)
        if midi is None or freq <= 0:
            self._freqs.clear(); self._ema = None
            ui.draw_text(surf, "—", self.f_big, ui.DIM, center=(W / 2, 200))
            ui.draw_text(surf, "toque uma corda", self.f_sm, ui.DIM, center=(W / 2, 300))
        else:
            self._freqs.append(freq)
            import numpy as np
            fmed = float(np.median(self._freqs))
            midi_f = freq_to_midi(fmed)
            m = int(round(midi_f))
            cents_raw = (midi_f - m) * 100
            self._ema = cents_raw if self._ema is None else 0.3 * cents_raw + 0.7 * self._ema
            cents = self._ema
            col = color_for_cents(cents)
            ui.draw_text(surf, midi_to_note(m), self.f_big, col, center=(W / 2, 200))
            ui.draw_text(surf, f"{fmed:.2f} Hz", self.f, ui.FG, center=(W / 2, 300))
            draw_cents_bar(surf, W / 2, 380, 280, cents)
            if abs(cents) <= CENTS_GREEN:
                msg, mc = "✓ AFINADO", ui.GREEN
            elif cents < 0:
                msg, mc = f"↑ subir ({abs(cents):.0f}¢)", col
            else:
                msg, mc = f"↓ descer ({cents:.0f}¢)", col
            ui.draw_text(surf, msg, self.f, mc, center=(W / 2, 440))
        self.btn_back.draw(surf)


# ============================================================ TREINO
CAL_FRETS = [0, 5, 7, 12]
DYNAMICS = ["FRACA", "MÉDIA", "FORTE"]
STRING_NAME = {6: "6ª (E grave)", 5: "5ª (A)", 4: "4ª (D)",
               3: "3ª (G)", 2: "2ª (B)", 1: "1ª (E aguda)"}


class TrainScreen:
    """Treino: assistente de calibração GUIADO (corda × casa × dinâmica) que valida
    e salva, + modo VALIDAÇÃO LIVRE (mostra nota + corda + casa + solta/pressionada)."""

    def __init__(self, app):
        self.app = app
        self.f_big = ui.font(96, bold=True)
        self.f_pos = ui.font(56, bold=True)   # posição (SOLTA / CASA N) — cabe na largura
        self.f = ui.font(22)
        self.f_sm = ui.font(15)
        self.f_title = ui.font(26, bold=True)
        self.mode = "intro"          # intro | calib | riff | done | live
        self.clf = None
        self.steps = []              # lista de dicts {string, fret, midi, dyn|None, name?}
        self.step_i = 0
        self.tries = 0
        self.status = ""
        self.last_detect = None
        self.session_tuning = app.state.tuning
        self.riff_name = ""
        self._sub_back = ui.Button((20, app.height - 56, 150, 40), "‹ Voltar", self._to_menu_or_intro, fnt=self.f_sm)
        cx = app.width / 2
        self.btn_calib = ui.Button((cx - 190, 228, 380, 50), "🎙  Calibração guiada (grade)", self._start_calib, fnt=self.f)
        self.btn_riff = ui.Button((cx - 190, 288, 380, 50), "🎵  Calibrar com riff (teste)", self._start_riff, fnt=self.f)
        self.btn_live = ui.Button((cx - 190, 348, 380, 50), "🎸  Validação livre", lambda: self._set_mode("live"), fnt=self.f)
        self.btn_menu = ui.Button((cx - 190, 408, 380, 46), "‹ Voltar ao menu", lambda: app.go("menu"), fnt=self.f_sm)

    # ---- navegação ----
    def _set_mode(self, m):
        self.mode = m
        if self.app.engine:
            while self.app.engine.poll_note() is not None:  # descarta notas pendentes
                pass

    def _to_menu_or_intro(self):
        if self.mode in ("calib", "riff", "done", "live"):
            self.mode = "intro"
        else:
            self.app.go("menu")

    def _new_clf(self, tuning_name):
        from classifier import FretClassifier
        self.clf = FretClassifier()
        self.clf.tuning_name = tuning_name
        self.session_tuning = tuning_name
        self.step_i = 0
        self.tries = 0
        self.last_detect = None

    # ---- calibração em grade ----
    def _start_calib(self):
        self._new_clf(self.app.state.tuning)
        tuning = TUNINGS[self.session_tuning]
        steps = []
        for s in range(6, 0, -1):
            open_midi = note_to_midi(list(reversed(tuning))[s - 1])
            for f in CAL_FRETS:
                for dyn in DYNAMICS:
                    steps.append({"string": s, "fret": f, "midi": open_midi + f, "dyn": dyn})
        self.steps = steps
        self.status = "Toque a posição indicada (som LIMPO / BYPASS)"
        self._set_mode("calib")

    # ---- calibração tocando um riff de teste ----
    def _start_riff(self):
        from charts import CHARTS
        from game import build_notes
        key = next((k for k, c in CHARTS.items() if c.category == "teste"), None)
        if key is None:
            return
        ch = CHARTS[key]
        self._new_clf(ch.tuning)
        self.riff_name = ch.name
        gns = build_notes(ch, ch.tuning)
        self.steps = [{"string": n.string_num, "fret": n.fret, "midi": n.midi,
                       "dyn": None, "name": n.name} for n in gns]
        self.status = "Toque as notas do riff na ordem (devagar)"
        self._set_mode("riff")

    def _cur_step(self):
        return self.steps[self.step_i]

    def _is_outlier(self, s, f, feats):
        vecs = self.clf.samples.get((s, f), [])
        if len(vecs) < 3:   # com poucas amostras o desvio é pouco confiável
            return False
        arr = np.stack(vecs)
        mean = arr.mean(axis=0)
        std = arr.std(axis=0)
        std[std < 1e-6] = 1.0
        return float(np.mean(np.abs((feats - mean) / std))) > 3.0

    def _update_capture(self):
        eng = self.app.engine
        if eng is None:
            self.status = "Sem áudio — configure em Dispositivo."
            return
        note = eng.poll_note()
        if note is None:
            return
        wave, f0, ts = note
        step = self._cur_step()
        s, f, exp_midi, dyn = step["string"], step["fret"], step["midi"], step["dyn"]
        det_f = freq_to_midi(f0)
        cents = (det_f - exp_midi) * 100
        if abs(cents) > 150:
            self.status = (f"Detectei {midi_to_note(int(round(det_f)))} ({cents:+.0f}¢) — "
                           f"esperado {midi_to_note(exp_midi)}. Toque de novo.")
            return
        res = eng.analyze_note(wave, f0, self.session_tuning)
        feats = res["features"]
        if self._is_outlier(s, f, feats) and self.tries < 2:
            self.tries += 1
            self.status = "⚠ amostra divergente — repita igual"
            return
        self.clf.add_calibration_sample(s, f, feats)
        self.last_detect = {"note": midi_to_note(exp_midi),
                            "is_open": res["is_open"], "dyn": dyn}
        self.tries = 0
        self.step_i += 1
        if self.step_i >= len(self.steps):
            self._finish_calib()
        else:
            self.status = "✓ capturado! Próxima."

    def _finish_calib(self):
        self.clf.save_calibration(SCRIPT_DIR / "calibration.json")
        if self.app.engine:
            self.app.engine.reload_classifier()
        self.mode = "done"

    # ---- loop ----
    def handle_event(self, ev):
        if self.mode == "intro":
            self.btn_calib.handle_event(ev)
            self.btn_riff.handle_event(ev)
            self.btn_live.handle_event(ev)
            self.btn_menu.handle_event(ev)
            return
        self._sub_back.handle_event(ev)
        if self.mode in ("calib", "riff") and ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_s and self.step_i < len(self.steps):   # pular
                self.step_i += 1
                self.tries = 0
                if self.step_i >= len(self.steps):
                    self._finish_calib()
            elif ev.key == pygame.K_r and self.step_i > 0:               # repetir anterior
                self.step_i -= 1
                self.tries = 0
        if self.mode == "done":
            self.btn_live.handle_event(ev)

    def update(self):
        if self.mode in ("calib", "riff"):
            self._update_capture()

    # ---- desenho ----
    def draw(self, surf):
        surf.fill(ui.BG)
        getattr(self, f"_draw_{self.mode}")(surf)

    def _draw_intro(self, surf):
        W = self.app.width
        ui.draw_text(surf, "Treino", self.f_title, ui.FG, midtop=(W / 2, 26))
        eng = self.app.engine
        if eng and eng.has_calibration():
            st, col = "✓ guitarra calibrada", ui.GREEN
        elif eng and eng.calibration_incompatible():
            st, col = "⚠ calibração desatualizada — recalibre", ui.YELLOW
        else:
            st, col = "ainda sem calibração — comece pela calibração guiada", ui.DIM
        ui.draw_text(surf, st, self.f_sm, col, midtop=(W / 2, 70))

        # explicação curta (linha a linha — sem quebra automática)
        expl = [
            "Calibração guiada: você toca cada corda em algumas casas e forças;",
            "o app aprende o timbre da SUA guitarra e passa a reconhecer",
            "corda, casa e se a nota é solta ou pressionada — inclusive no jogo.",
        ]
        y = 120
        for line in expl:
            ui.draw_text(surf, line, self.f_sm, ui.FG, midtop=(W / 2, y))
            y += 24
        ui.draw_text(surf, "Dica: ponha o som LIMPO (BYPASS) no TANK-G antes de calibrar.",
                     self.f_sm, ui.YELLOW, midtop=(W / 2, y + 6))

        self.btn_calib.draw(surf)
        self.btn_riff.draw(surf)
        self.btn_live.draw(surf)
        self.btn_menu.draw(surf)

    def _draw_progress(self, surf, title):
        W = self.app.width
        total = len(self.steps)
        done = min(self.step_i, total)
        ui.draw_text(surf, f"{title} — {done}/{total}", self.f_title, ui.FG, midtop=(W / 2, 24))
        pygame.draw.rect(surf, ui.PANEL, (W / 2 - 250, 64, 500, 10), border_radius=5)
        if total:
            pygame.draw.rect(surf, ui.GREEN, (W / 2 - 250, 64, int(500 * done / total), 10), border_radius=5)
        return total

    def _draw_status_block(self, surf):
        W = self.app.width
        scol = ui.GREEN if self.status.startswith("✓") else (
            ui.YELLOW if ("novo" in self.status or "⚠" in self.status) else ui.FG)
        ui.draw_text(surf, self.status, self.f_sm, scol, center=(W / 2, 348))
        if self.last_detect:
            d = self.last_detect
            tag = "solta" if d["is_open"] else "pressionada"
            extra = f" · {d['dyn']}" if d.get("dyn") else ""
            ui.draw_text(surf, f"última capturada: {d['note']} · {tag}{extra}",
                         self.f_sm, ui.DIM, center=(W / 2, 380))
        ui.draw_text(surf, "[S] pular   ·   [R] repetir anterior   ·   ESC cancela",
                     self.f_sm, ui.DIM, midtop=(W / 2, self.app.height - 92))
        self._sub_back.draw(surf)

    def _draw_calib(self, surf):
        W = self.app.width
        total = self._draw_progress(surf, "Calibração guiada")
        if self.step_i < total:
            step = self._cur_step()
            s, f, dyn = step["string"], step["fret"], step["dyn"]
            casa = "SOLTA" if f == 0 else f"CASA {f}"
            col = ui.LANE_COLORS[6 - s]
            ui.draw_text(surf, "Toque a posição abaixo — a captura é automática",
                         self.f_sm, ui.DIM, midtop=(W / 2, 96))
            ui.draw_text(surf, f"Corda {STRING_NAME[s]}", self.f, col, midtop=(W / 2, 132))
            ui.draw_text(surf, casa, self.f_pos, col, center=(W / 2, 215))
            ui.draw_text(surf, f"palhetada {dyn}", self.f, ui.ACCENT, center=(W / 2, 272))
            ui.draw_text(surf, f"nota esperada: {midi_to_note(step['midi'])}",
                         self.f_sm, ui.DIM, center=(W / 2, 306))
            self._draw_status_block(surf)
        else:
            self._sub_back.draw(surf)

    def _draw_riff(self, surf):
        W = self.app.width
        total = self._draw_progress(surf, f"Riff: {self.riff_name}")
        if self.step_i < total:
            step = self._cur_step()
            s, f = step["string"], step["fret"]
            casa = "solta" if f == 0 else f"casa {f}"
            col = ui.LANE_COLORS[6 - s]
            ui.draw_text(surf, "Toque a nota indicada (devagar) — captura automática",
                         self.f_sm, ui.DIM, midtop=(W / 2, 96))
            ui.draw_text(surf, step.get("name", midi_to_note(step["midi"])),
                         self.f_pos, ui.ACCENT, center=(W / 2, 200))
            ui.draw_text(surf, f"Corda {STRING_NAME[s]} · {casa}", self.f, col, center=(W / 2, 268))
            # próxima nota (preview)
            if self.step_i + 1 < total:
                nxt = self.steps[self.step_i + 1]
                ui.draw_text(surf, f"próxima: {nxt.get('name', midi_to_note(nxt['midi']))}",
                             self.f_sm, ui.DIM, center=(W / 2, 306))
            self._draw_status_block(surf)
        else:
            self._sub_back.draw(surf)

    def _draw_done(self, surf):
        W = self.app.width
        n = self.clf.n_calibrated_positions() if self.clf else 0
        ui.draw_text(surf, "✓ Calibração salva!", self.f_title, ui.GREEN, midtop=(W / 2, 60))
        ui.draw_text(surf, f"{n} posições calibradas", self.f, ui.FG, center=(W / 2, 150))
        ui.draw_text(surf, "O jogo e a validação já usam essa calibração.", self.f_sm, ui.DIM,
                     center=(W / 2, 190))
        self.btn_live.draw(surf)
        self._sub_back.draw(surf)

    def _draw_live(self, surf):
        W = self.app.width
        ui.draw_text(surf, "Validação livre — toque uma nota", self.f_title, ui.DIM, midtop=(W / 2, 24))
        eng = self.app.engine
        note = eng.poll_note() if eng else None
        if note is not None:
            wave, f0, ts = note
            self.last_detect = eng.analyze_note(wave, f0, self.app.state.tuning)
        d = self.last_detect
        if not d or not d.get("ranking"):
            mp = eng.current_pitch()[0] if eng else None
            ui.draw_text(surf, midi_to_note(mp) if mp is not None else "—",
                         self.f_big, ui.DIM if mp is None else ui.ACCENT, center=(W / 2, 200))
            ui.draw_text(surf, "toque uma nota", self.f_sm, ui.DIM, center=(W / 2, 300))
        else:
            s, f, conf = d["ranking"][0]
            note_name = midi_to_note(d["midi"])
            col = ui.LANE_COLORS[6 - s]
            ui.draw_text(surf, note_name, self.f_big, ui.ACCENT, center=(W / 2, 185))
            fl = "SOLTA" if f == 0 else f"casa {f}"
            conf_txt = f" ({conf*100:.0f}%)" if conf is not None else " (dica)"
            ui.draw_text(surf, f"Corda {s} — {fl}{conf_txt}", self.f, col, center=(W / 2, 285))
            tag = "SOLTA" if d["is_open"] else "PRESSIONADA"
            tcol = ui.GREEN if d["is_open"] else ui.YELLOW
            ui.draw_text(surf, tag, self.f, tcol, center=(W / 2, 330))
        src = "com calibração" if (eng and eng.has_calibration()) else "dica ergonômica (sem calibração)"
        ui.draw_text(surf, src, self.f_sm, ui.DIM, midtop=(W / 2, self.app.height - 92))
        self._sub_back.draw(surf)


# ============================================================ METRÔNOMO
class MetronomeScreen:
    """Metrônomo: BPM, acento (4/4), start/stop. O click é mixado na saída do
    AudioEngine — vai pro mesmo fone do monitor (full-duplex)."""

    def __init__(self, app):
        self.app = app
        self.f_title = ui.font(28, bold=True)
        self.f_bpm = ui.font(120, bold=True)
        self.f = ui.font(20)
        self.f_sm = ui.font(14)
        self._on_since = None    # wall-time de quando o metrônomo foi ligado (p/ pulse)
        cx, cy = app.width / 2, app.height / 2
        # botões de BPM
        self.btn_m10 = ui.Button((cx - 240, cy + 30, 70, 50), "−10", lambda: self._bump(-10), fnt=self.f)
        self.btn_m1 = ui.Button((cx - 160, cy + 30, 70, 50), "−1", lambda: self._bump(-1), fnt=self.f)
        self.btn_p1 = ui.Button((cx + 90, cy + 30, 70, 50), "+1", lambda: self._bump(+1), fnt=self.f)
        self.btn_p10 = ui.Button((cx + 170, cy + 30, 70, 50), "+10", lambda: self._bump(+10), fnt=self.f)
        self.btn_toggle = ui.Button((cx - 110, cy + 110, 220, 56), "", self._toggle, fnt=self.f,
                                     color=(40, 80, 60), hover=(55, 105, 80))
        self.btn_accent = ui.Button((cx - 110, cy + 180, 220, 36), "", self._toggle_accent, fnt=self.f_sm)
        self.btn_in_game = ui.Button((cx - 110, cy + 222, 220, 36), "", self._toggle_in_game, fnt=self.f_sm)
        self.btn_back = ui.Button((20, app.height - 56, 150, 40), "‹ Voltar",
                                  self._back, fnt=self.f_sm)

    def _bump(self, delta: int):
        st = self.app.state
        st.metronome_bpm = max(20, min(300, st.metronome_bpm + delta))
        if self.app.engine:
            self.app.engine.set_metronome(self.app.engine.metronome_on, bpm=st.metronome_bpm)
        st.save()

    def _toggle(self):
        eng = self.app.engine
        if eng is None:
            return
        on = not eng.metronome_on
        eng.set_metronome(on, bpm=self.app.state.metronome_bpm,
                          accent_every=4 if self.app.state.metronome_accent else 0,
                          beat_offset=0)
        self._on_since = time.time() if eng.metronome_on else None

    def _toggle_accent(self):
        st = self.app.state
        st.metronome_accent = not st.metronome_accent
        if self.app.engine:
            self.app.engine.set_metronome(self.app.engine.metronome_on,
                                          accent_every=4 if st.metronome_accent else 0)
        st.save()

    def _toggle_in_game(self):
        st = self.app.state
        st.metronome_in_game = not st.metronome_in_game
        st.save()

    def _back(self):
        # desliga o metrônomo ao sair (evita ficar tocando em outras telas)
        if self.app.engine and self.app.engine.metronome_on:
            self.app.engine.set_metronome(False)
        self.app.go("menu")

    def on_exit(self):
        # silencia ao sair da tela do metrônomo (mantém p/ jogo via lifecycle do jogo)
        if self.app.engine and self.app.engine.metronome_on:
            self.app.engine.set_metronome(False)

    def handle_event(self, ev):
        for b in (self.btn_m10, self.btn_m1, self.btn_p1, self.btn_p10,
                  self.btn_toggle, self.btn_accent, self.btn_in_game, self.btn_back):
            b.handle_event(ev)
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_SPACE:
                self._toggle()
            elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self._bump(+1)
            elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self._bump(-1)

    def update(self):
        pass

    def draw(self, surf):
        surf.fill(ui.BG)
        W, H = self.app.width, self.app.height
        cx, cy = W / 2, H / 2
        eng = self.app.engine
        on = bool(eng and eng.metronome_on)
        ui.draw_text(surf, "Metrônomo", self.f_title, ui.FG, midtop=(cx, 30))

        # BPM gigante (cor pulsa quando ligado)
        bpm_col = ui.GREEN if on else ui.DIM
        ui.draw_text(surf, str(self.app.state.metronome_bpm), self.f_bpm, bpm_col,
                     center=(cx, cy - 50))
        ui.draw_text(surf, "BPM", self.f_sm, ui.DIM, center=(cx, cy + 10))

        # pulse visual sincronizado com o click (quando tocando)
        if on and self._on_since is not None:
            spb = 60.0 / max(1, eng.metronome_bpm)
            t = time.time() - self._on_since
            phase = (t % spb) / spb
            intensity = max(0.0, 1.0 - phase * 3.0)
            beat_k = int(t / spb)
            is_accent = (eng.metronome_accent_every > 0
                         and ((beat_k - eng.metronome_beat_offset) % eng.metronome_accent_every) == 0)
            ui.draw_beat_pulse(surf, cx, cy + 60, intensity, is_accent, base_radius=22)

        # botões ± rotulados
        for b in (self.btn_m10, self.btn_m1, self.btn_p1, self.btn_p10):
            b.draw(surf)

        # start/stop
        self.btn_toggle.label = "■ PARAR" if on else "▶ TOCAR"
        self.btn_toggle.draw(surf)

        # acento
        self.btn_accent.label = ("Acento 4/4: ON" if self.app.state.metronome_accent
                                 else "Acento 4/4: OFF")
        self.btn_accent.draw(surf)
        # tocar durante o jogo
        self.btn_in_game.label = ("Tocar no jogo: ON" if self.app.state.metronome_in_game
                                   else "Tocar no jogo: OFF")
        self.btn_in_game.draw(surf)

        # disponibilidade
        if eng is None:
            ui.draw_text(surf, "(sem áudio)", self.f_sm, ui.YELLOW, midtop=(cx, H - 100))
        elif not eng.monitor_available:
            ui.draw_text(surf, "(saída de áudio indisponível — full-duplex falhou)",
                         self.f_sm, ui.YELLOW, midtop=(cx, H - 100))
        else:
            ui.draw_text(surf, "espaço = liga/desliga · + / − ajusta BPM",
                         self.f_sm, ui.DIM, midtop=(cx, H - 100))
        self.btn_back.draw(surf)


# ============================================================ SELEÇÃO DE MÚSICA
class SongSelectScreen:
    """Lista as músicas/riffs (categorias 'musica' e 'teste'); seleciona e joga."""

    def __init__(self, app):
        self.app = app
        self.f_title = ui.font(28, bold=True)
        self.f = ui.font(18)
        self.f_sm = ui.font(14)
        self.buttons = []
        self._build()
        self.btn_back = ui.Button((20, app.height - 56, 150, 40), "‹ Voltar",
                                  lambda: app.go("menu"), fnt=self.f_sm)

    def _build(self):
        from charts import CHARTS
        W = self.app.width
        keys = sorted(CHARTS, key=lambda k: (CHARTS[k].category != "musica", k))
        bw, bh, gap = 600, 50, 12
        x = W / 2 - bw / 2
        y = 110
        for k in keys:
            ch = CHARTS[k]
            tag = "🎵" if ch.category == "musica" else "🧪"
            label = f"{tag} {ch.name}  ({ch.bpm} BPM · {len(ch.notes)} notas)"
            self.buttons.append(ui.Button((x, y, bw, bh), label,
                                          (lambda kk=k: self._play(kk)), fnt=self.f))
            y += bh + gap

    def _play(self, key):
        self.app.state.chart = key
        self.app.state.save()
        self.app.go("game")

    def handle_event(self, ev):
        for b in self.buttons:
            b.handle_event(ev)
        self.btn_back.handle_event(ev)

    def update(self):
        pass

    def draw(self, surf):
        surf.fill(ui.BG)
        W = self.app.width
        ui.draw_text(surf, "Escolha a música / riff", self.f_title, ui.FG, midtop=(W / 2, 42))
        ui.draw_text(surf, "🎵 músicas    ·    🧪 testes (lentos, p/ validar e calibrar)",
                     self.f_sm, ui.DIM, midtop=(W / 2, 80))
        for b in self.buttons:
            b.draw(surf)
        ui.draw_text(surf, f"atual: {self.app.state.chart}", self.f_sm, ui.DIM,
                     midtop=(W / 2, self.app.height - 86))
        self.btn_back.draw(surf)
