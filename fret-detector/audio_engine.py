"""Motor de áudio: captura em thread, detecta pitch (YIN) e ataques (onset),
e opcionalmente faz MONITOR (reproduz a guitarra no fone do PC, full-duplex).

- poll_onset() -> (midi, ts) | None       # consome 1 ataque (pluck)
- current_pitch() -> (midi|None, freq)
- current_rms() -> float                    # nível de sinal (p/ barra de nível)
- classify_current(tuning) -> (string, fret, conf|None) | None   # dica de corda/casa
- set_monitor(on, gain=None)                # liga/desliga o passthrough p/ o fone
- set_output_device(dev)

Quando monitor_on, abre full-duplex (sd.Stream input+output); senão InputStream
(comportamento leve, usado pelo jogo). Se full-duplex falhar, cai pra InputStream
e marca monitor_available=False.
"""
import threading
import time
from pathlib import Path
import numpy as np
import sounddevice as sd

from fret_detector import (
    SAMPLE_RATE, HOP_SIZE, MIN_FREQ, MAX_FREQ,
    yin, freq_to_midi, fret_positions, find_tank_g_device,
)

BUFFER_SIZE = 2048  # ~46 ms
SCRIPT_DIR = Path(__file__).resolve().parent


class AudioEngine:
    def __init__(self, device=None, gain=40.0, output_device=None,
                 monitor_on=False, monitor_gain=12.0,
                 silence_rms=0.004, attack_rms=0.015):
        self.device = device if device is not None else find_tank_g_device()
        self.output_device = output_device
        self.gain = gain
        self.monitor_on = monitor_on
        self.monitor_gain = monitor_gain
        self.silence_rms = silence_rms
        self.attack_rms = attack_rms

        self.buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
        self._lock = threading.Lock()
        self._running = False
        self.stream = None
        self.monitor_available = True   # vira False se full-duplex falhar
        self.monitor_error = ""         # última mensagem de erro do full-duplex

        self._cur_midi = None
        self._cur_freq = 0.0
        self._cur_rms = 0.0
        self._cur_buf = None            # cópia do buffer no último pitch (p/ classify)

        self._armed = True
        self._pending_onset = None

        # classificador opcional (dica de corda/casa)
        self._classifier = None
        self._load_classifier()

    def _load_classifier(self):
        calib = SCRIPT_DIR / "calibration.json"
        if not calib.exists():
            return
        try:
            from classifier import FretClassifier
            clf = FretClassifier()
            if clf.load(calib, SCRIPT_DIR / "corrections.json"):
                self._classifier = clf
        except Exception:
            self._classifier = None

    def has_calibration(self) -> bool:
        return self._classifier is not None

    # ---- ciclo de vida ----
    def start(self):
        if self.device is None:
            raise RuntimeError("Nenhum dispositivo de entrada encontrado (use device=N).")
        self._running = True
        if self.monitor_on:
            self._open_duplex()
        else:
            self._open_input()

    def _open_input(self):
        self.stream = sd.InputStream(
            device=self.device, samplerate=SAMPLE_RATE, channels=1,
            blocksize=HOP_SIZE, callback=self._cb_input,
        )
        self.stream.start()

    def _open_duplex(self):
        # tenta a saída escolhida; se falhar (ex.: HS317 em host API incompatível),
        # tenta a saída PADRÃO do sistema antes de desistir do monitor.
        candidates = [self.output_device]
        if self.output_device is not None:
            candidates.append(None)
        last_err = None
        for out in candidates:
            try:
                self.stream = sd.Stream(
                    device=(self.device, out),
                    samplerate=SAMPLE_RATE, blocksize=HOP_SIZE,
                    channels=(1, 2), callback=self._cb_duplex,
                )
                self.stream.start()
                self.monitor_available = True
                self.monitor_error = ""
                self.output_device = out   # usa o que abriu
                return
            except Exception as e:
                last_err = e
        # nenhum funcionou → captura simples (monitor off)
        self.monitor_available = False
        self.monitor_on = False
        self.monitor_error = f"{type(last_err).__name__}: {str(last_err)[:90]}"
        self._open_input()

    def _reopen(self):
        if self.stream is not None:
            try:
                self.stream.stop(); self.stream.close()
            except Exception:
                pass
            self.stream = None
        if not self._running:
            return
        if self.monitor_on:
            self._open_duplex()
        else:
            self._open_input()

    def stop(self):
        self._running = False
        if self.stream is not None:
            try:
                self.stream.stop(); self.stream.close()
            except Exception:
                pass
            self.stream = None

    def device_name(self) -> str:
        if self.device is None:
            return "—"
        try:
            return sd.query_devices(self.device)["name"]
        except Exception:
            return str(self.device)

    # ---- controles de monitor ----
    def set_monitor(self, on: bool, gain: float | None = None):
        if gain is not None:
            self.monitor_gain = gain
        if on != self.monitor_on:
            self.monitor_on = on
            self._reopen()

    def set_output_device(self, dev):
        self.output_device = dev
        if self.monitor_on:
            self._reopen()

    def set_input_device(self, dev):
        self.device = dev
        self._reopen()

    # ---- análise comum ----
    def _analyze(self, mono):
        new_audio = mono * self.gain
        self.buffer = np.concatenate([self.buffer[len(new_audio):], new_audio])
        rms = float(np.sqrt(np.mean(self.buffer * self.buffer)))

        with self._lock:
            self._cur_rms = rms

        if rms < self.silence_rms:
            self._armed = True
            with self._lock:
                self._cur_midi = None
                self._cur_freq = 0.0
            return

        freq = yin(self.buffer, SAMPLE_RATE)
        if freq < MIN_FREQ or freq > MAX_FREQ:
            return

        midi = int(round(freq_to_midi(freq)))
        with self._lock:
            self._cur_midi = midi
            self._cur_freq = freq
            self._cur_buf = self.buffer.copy()

        if self._armed and rms >= self.attack_rms:
            self._armed = False
            with self._lock:
                self._pending_onset = (midi, time.time())

    # ---- callbacks ----
    def _cb_input(self, indata, frames, time_info, status):
        if self._running:
            self._analyze(indata[:, 0])

    def _cb_duplex(self, indata, outdata, frames, time_info, status):
        if not self._running:
            outdata.fill(0)
            return
        self._analyze(indata[:, 0])
        if self.monitor_on:
            mono = np.clip(indata[:, 0] * self.monitor_gain, -1.0, 1.0)
            outdata[:, 0] = mono
            outdata[:, 1] = mono
        else:
            outdata.fill(0)

    # ---- API consumida pelas telas/jogo ----
    def poll_onset(self):
        with self._lock:
            onset = self._pending_onset
            self._pending_onset = None
        return onset

    def current_pitch(self):
        with self._lock:
            return self._cur_midi, self._cur_freq

    def current_rms(self) -> float:
        with self._lock:
            return self._cur_rms

    def classify_current(self, tuning_name: str):
        """Dica de corda/casa pra nota tocada agora. Usa o classificador (se houver
        calibração) ou a posição ergonômica. Retorna (string, fret, conf|None)."""
        with self._lock:
            midi = self._cur_midi
            buf = None if self._cur_buf is None else self._cur_buf
            freq = self._cur_freq
        if midi is None:
            return None
        if self._classifier is not None and buf is not None:
            try:
                from features import extract_features
                feats = extract_features(buf, SAMPLE_RATE, freq)
                ranking = self._classifier.classify(feats, midi, tuning_name)
                if ranking:
                    s, f, c = ranking[0]
                    return s, f, c
            except Exception:
                pass
        # fallback ergonômico: menor casa
        from fret_detector import TUNINGS
        pos = fret_positions(midi, TUNINGS[tuning_name])
        if not pos:
            return None
        s, f = min(pos, key=lambda sf: (sf[1], sf[0]))
        return s, f, None


# ---- detector de onset reutilizável p/ testes offline (sem sounddevice) ----
class OnsetDetector:
    """Mesma lógica de onset do AudioEngine, alimentada manualmente (testes)."""
    def __init__(self, silence_rms=0.004, attack_rms=0.015):
        self.silence_rms = silence_rms
        self.attack_rms = attack_rms
        self.buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
        self._armed = True

    def push(self, block: np.ndarray, ts: float):
        self.buffer = np.concatenate([self.buffer[len(block):], block])
        rms = float(np.sqrt(np.mean(self.buffer * self.buffer)))
        if rms < self.silence_rms:
            self._armed = True
            return None
        freq = yin(self.buffer, SAMPLE_RATE)
        if freq < MIN_FREQ or freq > MAX_FREQ:
            return None
        if self._armed and rms >= self.attack_rms:
            self._armed = False
            return int(round(freq_to_midi(freq))), ts
        return None
