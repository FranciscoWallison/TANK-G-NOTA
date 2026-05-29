"""Telas do TANK-G Studio: Menu (hub), Dispositivo, Afinador, Treino.

Cada tela recebe o `app` (studio) e expõe handle_event/update/draw(surf).
Navega via app.go("menu"|"device"|"tuner"|"train"|"game").
"""
from collections import deque
import pygame
import sounddevice as sd

import ui
from fret_detector import (
    freq_to_midi, midi_to_note, TUNINGS, find_tank_g_device,
)

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
            ui.Button((bx, y0 + 3 * (bh + gap), bw, bh), "🎮  Jogar música", lambda: app.go("game"),
                      color=(40, 80, 60), hover=(55, 105, 80)),
        ]
        # toggles na base
        self.btn_monitor = ui.Button((bx, y0 + 4 * (bh + gap) + 10, 155, 46), "", self._toggle_monitor, fnt=self.f_sm)
        self.btn_diff = ui.Button((bx + 165, y0 + 4 * (bh + gap) + 10, 155, 46), "", self._cycle_diff, fnt=self.f_sm)

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
        ui.draw_text(surf, "ESC sai", self.f_sm, ui.DIM, midtop=(W / 2, self.app.height - 26))


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
class TrainScreen:
    def __init__(self, app):
        self.app = app
        self.f_big = ui.font(110, bold=True)
        self.f = ui.font(22)
        self.f_sm = ui.font(15)
        self.f_title = ui.font(26, bold=True)
        self.btn_back = ui.Button((20, app.height - 60, 160, 42), "‹ Voltar (ESC)", lambda: app.go("menu"), fnt=self.f_sm)

    def handle_event(self, ev):
        self.btn_back.handle_event(ev)

    def update(self):
        pass

    def draw(self, surf):
        surf.fill(ui.BG)
        W = self.app.width
        ui.draw_text(surf, "Treino — valida a nota tocada", self.f_title, ui.DIM, midtop=(W / 2, 20))
        eng = self.app.engine
        midi, freq = eng.current_pitch() if eng else (None, 0)
        if midi is None or freq <= 0:
            ui.draw_text(surf, "—", self.f_big, ui.DIM, center=(W / 2, 210))
            ui.draw_text(surf, "toque uma nota", self.f_sm, ui.DIM, center=(W / 2, 310))
        else:
            ui.draw_text(surf, midi_to_note(midi), self.f_big, ui.ACCENT, center=(W / 2, 200))
            ui.draw_text(surf, f"{freq:.1f} Hz", self.f, ui.FG, center=(W / 2, 290))
            hint = eng.classify_current(self.app.state.tuning)
            if hint:
                s, f, conf = hint
                col = ui.LANE_COLORS[6 - s]
                fl = "solta" if f == 0 else f"casa {f}"
                conf_txt = f" ({conf*100:.0f}%)" if conf is not None else "  (dica)"
                ui.draw_text(surf, f"Corda {s} — {fl}{conf_txt}", self.f, col, center=(W / 2, 350))
        src = "com calibração" if (eng and eng.has_calibration()) else "dica ergonômica (sem calibração)"
        ui.draw_text(surf, src, self.f_sm, ui.DIM, midtop=(W / 2, self.app.height - 90))
        self.btn_back.draw(surf)
