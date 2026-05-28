"""Afinador visual (GUI Tkinter) para o TANK-G.

Mostra:
    - Nota detectada (gigante)
    - Frequência em Hz
    - Régua de cents (-50 a +50) com agulha
    - Fundo verde/amarelo/vermelho indicando proximidade
    - Indicação de subir/descer
    - Botões pra escolher afinação alvo (auto, E std, Eb, Drop D, Drop B, Drop C)

Uso:
    python tuner.py                              # auto-detecta TANK-G
    python tuner.py --device 2 --gain 20         # forçando ID/gain
    python tuner.py --tuning eb                  # já abre na afinação alvo
"""
import argparse
import sys
import threading
import time
import tkinter as tk
from collections import deque
import numpy as np
import sounddevice as sd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fret_detector import (
    SAMPLE_RATE, HOP_SIZE, MIN_FREQ, MAX_FREQ, TUNINGS,
    yin, freq_to_midi, midi_to_note, note_to_midi, find_tank_g_device,
)

# Tuner usa buffer MAIOR que o detector — mais precisão (latência aceitável pra afinar)
TUNER_BUFFER_SIZE = 4096  # ~93 ms

# Visual
WIDTH, HEIGHT = 720, 480
BG = "#1e1e1e"
FG = "#f0f0f0"
DIM = "#777777"
GREEN = "#4caf50"
YELLOW = "#ffc107"
RED = "#f44336"
CENTS_RANGE = 50  # mostra -50 a +50
CENTS_GREEN = 5   # dentro de ±5¢ = afinado
CENTS_YELLOW = 15 # ±15¢ = perto

UPDATE_MS = 60
SILENCE_RMS = 0.001

# Presets de suavização: (janela_mediana, ema_alpha, histerese_frames)
# - janela_mediana: nº de leituras de freq pra tirar mediana (mata outliers)
# - ema_alpha:     peso da nova leitura no EMA dos cents (1.0 = sem suavização)
# - histerese:     nº de frames consecutivos pra trocar a nota exibida
SMOOTHING_PRESETS = {
    "off":    (1, 1.0, 1),
    "low":    (3, 0.45, 2),
    "medium": (5, 0.25, 3),
    "high":   (9, 0.12, 5),
}


def color_for_cents(cents: float) -> str:
    a = abs(cents)
    if a <= CENTS_GREEN:
        return GREEN
    if a <= CENTS_YELLOW:
        return YELLOW
    return RED


class Tuner:
    def __init__(self, device: int, gain: float, target_tuning: str | None,
                 smoothing: str = "medium"):
        self.device = device
        self.gain = gain
        self.target_tuning = target_tuning  # None = auto (nota mais próxima); senão nome da afinação
        self.buffer = np.zeros(TUNER_BUFFER_SIZE, dtype=np.float32)

        median_n, ema_alpha, hyst = SMOOTHING_PRESETS[smoothing]
        self.median_n = median_n
        self.ema_alpha = ema_alpha
        self.hysteresis_frames = hyst

        # Buffers de suavização (acessados só na thread de áudio)
        self._freq_hist: deque[float] = deque(maxlen=median_n)
        self._ema_cents: float | None = None
        self._candidate_midi: int | None = None
        self._candidate_count = 0
        self._displayed_midi: int | None = None

        # Estado compartilhado entre thread de áudio e GUI
        self._lock = threading.Lock()
        self._latest: dict | None = None
        self._running = True

        # GUI
        self.root = tk.Tk()
        self.root.title("🎸 TANK-G Tuner")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.configure(bg=BG)
        self.root.minsize(560, 380)

        self._build_ui()
        self._start_audio()
        self.root.after(UPDATE_MS, self._refresh)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Top: nome da afinação alvo + status
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=14, pady=(10, 0))

        tk.Label(top, text="Afinação alvo:", bg=BG, fg=DIM,
                 font=("Segoe UI", 10)).pack(side="left")

        self.tuning_var = tk.StringVar(value=self.target_tuning or "auto")
        choices = ["auto", "standard", "eb", "drop-d", "drop-c", "drop-b", "drop-a"]
        self.tuning_menu = tk.OptionMenu(top, self.tuning_var, *choices,
                                          command=self._on_tuning_change)
        self.tuning_menu.configure(bg="#333", fg=FG, activebackground="#444",
                                    activeforeground=FG, font=("Segoe UI", 10),
                                    relief="flat", highlightthickness=0,
                                    borderwidth=0)
        self.tuning_menu["menu"].configure(bg="#333", fg=FG)
        self.tuning_menu.pack(side="left", padx=(8, 0))

        self.status_label = tk.Label(top, text="🎙️  ouvindo...", bg=BG, fg=DIM,
                                      font=("Segoe UI", 10))
        self.status_label.pack(side="right")

        # Centro: nota gigante
        self.note_label = tk.Label(self.root, text="—", bg=BG, fg=FG,
                                    font=("Consolas", 120, "bold"))
        self.note_label.pack(pady=(20, 0))

        # Freq pequena + alvo
        self.freq_label = tk.Label(self.root, text="0.00 Hz", bg=BG, fg=DIM,
                                    font=("Consolas", 16))
        self.freq_label.pack()

        self.target_label = tk.Label(self.root, text="alvo: —", bg=BG, fg=DIM,
                                      font=("Segoe UI", 12))
        self.target_label.pack(pady=(2, 14))

        # Barra de cents (Canvas)
        self.bar_canvas = tk.Canvas(self.root, height=70, bg=BG,
                                     highlightthickness=0)
        self.bar_canvas.pack(fill="x", padx=40)
        self.bar_canvas.bind("<Configure>", lambda e: self._draw_bar(self._last_cents or 0))

        # Instrução (subir/descer)
        self.action_label = tk.Label(self.root, text="", bg=BG, fg=DIM,
                                      font=("Segoe UI", 14, "bold"))
        self.action_label.pack(pady=(8, 0))

        # Cents numérico
        self.cents_label = tk.Label(self.root, text="0¢", bg=BG, fg=DIM,
                                     font=("Consolas", 14))
        self.cents_label.pack(pady=(2, 8))

        self._last_cents = 0.0
        self._draw_bar(0)

    def _draw_bar(self, cents: float):
        c = self.bar_canvas
        c.delete("all")
        w = c.winfo_width() or WIDTH - 80
        h = c.winfo_height() or 70
        mid = w // 2

        # Trilha de fundo (gradiente em 3 faixas)
        c.create_rectangle(0, h // 2 - 6, w, h // 2 + 6, fill="#2b2b2b", outline="")
        # Faixas verde, amarela, vermelha
        green_half = int((CENTS_GREEN / CENTS_RANGE) * (w / 2))
        yellow_half = int((CENTS_YELLOW / CENTS_RANGE) * (w / 2))
        c.create_rectangle(mid - green_half, h // 2 - 6, mid + green_half,
                           h // 2 + 6, fill=GREEN, outline="")
        c.create_rectangle(mid - yellow_half, h // 2 - 6, mid - green_half,
                           h // 2 + 6, fill=YELLOW, outline="")
        c.create_rectangle(mid + green_half, h // 2 - 6, mid + yellow_half,
                           h // 2 + 6, fill=YELLOW, outline="")
        c.create_rectangle(0, h // 2 - 6, mid - yellow_half, h // 2 + 6,
                           fill=RED, outline="")
        c.create_rectangle(mid + yellow_half, h // 2 - 6, w, h // 2 + 6,
                           fill=RED, outline="")

        # Ticks
        for cent in (-50, -25, -15, -5, 0, 5, 15, 25, 50):
            x = mid + int((cent / CENTS_RANGE) * (w / 2))
            tick_h = 10 if cent in (-50, 0, 50) else 6
            c.create_line(x, h // 2 + 8, x, h // 2 + 8 + tick_h, fill=DIM)
            if cent in (-50, -25, 0, 25, 50):
                c.create_text(x, h // 2 + 26, text=f"{cent:+d}", fill=DIM,
                              font=("Consolas", 9))

        # Agulha
        cents_clamped = max(-CENTS_RANGE, min(CENTS_RANGE, cents))
        nx = mid + int((cents_clamped / CENTS_RANGE) * (w / 2))
        col = color_for_cents(cents)
        c.create_polygon(nx - 8, h // 2 - 22, nx + 8, h // 2 - 22, nx, h // 2 - 6,
                         fill=col, outline=col)
        c.create_rectangle(nx - 2, h // 2 - 6, nx + 2, h // 2 + 6, fill=col,
                           outline=col)

    def _on_tuning_change(self, value):
        self.target_tuning = None if value == "auto" else value

    def _on_close(self):
        self._running = False
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass
        self.root.destroy()

    def _start_audio(self):
        try:
            self.stream = sd.InputStream(
                device=self.device, samplerate=SAMPLE_RATE, channels=1,
                blocksize=HOP_SIZE, callback=self._audio_callback,
            )
            self.stream.start()
        except Exception as e:
            self.status_label.configure(text=f"❌ Erro áudio: {e}", fg=RED)

    def _audio_callback(self, indata, frames, time_info, status):
        if not self._running:
            return
        new_audio = indata[:, 0] * self.gain
        self.buffer = np.concatenate([self.buffer[len(new_audio):], new_audio])

        rms = float(np.sqrt(np.mean(self.buffer * self.buffer)))
        if rms < SILENCE_RMS:
            # Silêncio: limpa histórico pra próxima nota começar fresca
            if rms < SILENCE_RMS * 0.5:
                self._freq_hist.clear()
                self._ema_cents = None
                self._candidate_midi = None
                self._candidate_count = 0
            return

        freq_raw = yin(self.buffer, SAMPLE_RATE)
        if freq_raw < MIN_FREQ or freq_raw > MAX_FREQ:
            return

        # 1. Filtro de mediana na frequência (mata outliers/octava errada)
        self._freq_hist.append(freq_raw)
        freq = float(np.median(self._freq_hist))

        midi_f = freq_to_midi(freq)
        if self.target_tuning is None:
            # Histerese: só troca a nota exibida após N frames consistentes
            detected_midi = int(round(midi_f))
            if detected_midi == self._candidate_midi:
                self._candidate_count += 1
            else:
                self._candidate_midi = detected_midi
                self._candidate_count = 1
            if self._displayed_midi is None or self._candidate_count >= self.hysteresis_frames:
                self._displayed_midi = detected_midi
            target_midi = self._displayed_midi
        else:
            # Corda mais próxima dentro da afinação alvo (sem histerese — já é estável)
            targets = [note_to_midi(n) for n in TUNINGS[self.target_tuning]]
            target_midi = min(targets, key=lambda m: abs(m - midi_f))
            self._displayed_midi = target_midi

        cents_raw = (midi_f - target_midi) * 100

        # 2. EMA nos cents (suaviza agulha)
        if self._ema_cents is None:
            self._ema_cents = cents_raw
        else:
            self._ema_cents = self.ema_alpha * cents_raw + (1 - self.ema_alpha) * self._ema_cents
        cents = self._ema_cents

        with self._lock:
            self._latest = {
                "freq": freq,
                "midi_f": midi_f,
                "target_midi": target_midi,
                "cents": cents,
                "rms": rms,
                "ts": time.time(),
            }

    def _refresh(self):
        if not self._running:
            return
        with self._lock:
            data = self._latest

        if data is None or (time.time() - data["ts"]) > 0.6:
            self.note_label.configure(text="—", fg=DIM)
            self.freq_label.configure(text="0.00 Hz", fg=DIM)
            self.target_label.configure(text="aguardando som...", fg=DIM)
            self.action_label.configure(text="")
            self.cents_label.configure(text="0¢", fg=DIM)
            self._draw_bar(0)
            self._last_cents = 0
            self.status_label.configure(text="🎙️  silêncio", fg=DIM)
        else:
            cents = data["cents"]
            col = color_for_cents(cents)
            target_note = midi_to_note(data["target_midi"])
            target_freq = 440.0 * (2 ** ((data["target_midi"] - 69) / 12))

            self.note_label.configure(text=target_note, fg=col)
            self.freq_label.configure(text=f"{data['freq']:.2f} Hz", fg=FG)
            tuning_str = self.target_tuning or "auto (cromático)"
            self.target_label.configure(
                text=f"alvo: {target_note} ({target_freq:.2f} Hz) · {tuning_str}",
                fg=DIM,
            )

            if abs(cents) <= CENTS_GREEN:
                self.action_label.configure(text="✓ AFINADO", fg=GREEN)
            elif cents < 0:
                self.action_label.configure(text=f"↑ subir  ({abs(cents):.0f}¢)", fg=col)
            else:
                self.action_label.configure(text=f"↓ descer  ({cents:.0f}¢)", fg=col)

            self.cents_label.configure(text=f"{cents:+.1f}¢", fg=col)
            self._draw_bar(cents)
            self._last_cents = cents
            self.status_label.configure(text="🎙️  ouvindo", fg=GREEN)

        self.root.after(UPDATE_MS, self._refresh)

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, help="ID do dispositivo de entrada")
    parser.add_argument("--gain", type=float, default=20.0,
                        help="Multiplicador de ganho (default 20.0 — sinal fraco do TANK-G via USB)")
    parser.add_argument("--tuning", choices=["auto"] + list(TUNINGS.keys()), default="auto",
                        help="Afinação alvo inicial (default auto = nota cromática mais próxima)")
    parser.add_argument("--smoothing", choices=list(SMOOTHING_PRESETS.keys()), default="medium",
                        help="Nível de suavização: off / low / medium (default) / high")
    args = parser.parse_args()

    if args.device is None:
        device = find_tank_g_device()
        if device is None:
            print("⚠️  TANK-G não encontrado. Usando dispositivo padrão.")
            device = sd.default.device[0]
    else:
        device = args.device

    print(f"🎸 Capturando de device {device} | gain {args.gain}x | alvo {args.tuning} | smoothing {args.smoothing}")
    tuner = Tuner(device=device, gain=args.gain,
                  target_tuning=None if args.tuning == "auto" else args.tuning,
                  smoothing=args.smoothing)
    tuner.run()


if __name__ == "__main__":
    main()
