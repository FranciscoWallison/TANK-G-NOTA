"""Motor de áudio: captura em thread, detecta pitch (YIN), ataques (onset),
captura a NOTA INTEIRA (~0.5s) para features temporais, classifica corda/casa +
solta/pressionada, e opcionalmente faz MONITOR (reproduz a guitarra no fone do PC).

API consumida pelas telas/jogo:
  poll_onset()  -> (midi, ts) | None        # ataque instantâneo (timing)
  poll_note()   -> (waveform, f0, ts) | None # nota completa (~0.5s) p/ classificar
  analyze_note(wave, f0, tuning) -> dict     # features + is_open + ranking
  classify_current(tuning) -> (s,f,conf)|None
  current_pitch() / current_rms()
  set_monitor(on, gain) / set_output_device / set_input_device / reload_classifier
"""
import threading
import time
from pathlib import Path
import numpy as np
import sounddevice as sd

from fret_detector import (
    SAMPLE_RATE, HOP_SIZE, MIN_FREQ, MAX_FREQ, TUNINGS,
    yin, freq_to_midi, fret_positions, find_tank_g_device,
)

BUFFER_SIZE = 2048        # ~46 ms — janela do YIN/pitch
NOTE_WINDOW = 0.5         # s — janela da nota inteira p/ features temporais
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SUSTAIN_THRESHOLD = 0.4   # fallback quando sem calibração


class AudioEngine:
    def __init__(self, device=None, gain=40.0, output_device=None,
                 monitor_on=False, monitor_gain=12.0,
                 metronome_on=False, metronome_bpm=100, metronome_accent_every=4,
                 metronome_gain=0.6, metronome_beat_offset=0,
                 silence_rms=0.004, attack_rms=0.015):
        self.device = device if device is not None else find_tank_g_device()
        self.output_device = output_device
        self.gain = gain
        self.monitor_on = monitor_on
        self.monitor_gain = monitor_gain
        self.metronome_on = metronome_on
        self.metronome_bpm = max(20, min(300, int(metronome_bpm)))
        self.metronome_accent_every = max(0, int(metronome_accent_every))  # 0 = sem acento
        self.metronome_beat_offset = int(metronome_beat_offset)  # desloca onde cai o acento
        self.metronome_gain = metronome_gain
        self.silence_rms = silence_rms
        self.attack_rms = attack_rms

        # click do metrônomo (pré-computado)
        self._click_normal, self._click_accent = self._make_clicks(SAMPLE_RATE)
        self._metro_sample = 0               # contador de amostras desde que ligou
        self._active_click = None            # (waveform, abs_start_sample) ainda renderizando

        self.buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
        self._lock = threading.Lock()
        self._running = False
        self.stream = None
        self.monitor_available = True
        self.monitor_error = ""

        self._cur_midi = None
        self._cur_freq = 0.0
        self._cur_rms = 0.0

        self._armed = True
        self._pending_onset = None

        # captura da nota inteira
        self._note_target = int(NOTE_WINDOW * SAMPLE_RATE)
        self._note_capturing = False
        self._note_chunks: list[np.ndarray] = []
        self._note_collected = 0
        self._note_f0 = 0.0
        self._note_ts = 0.0
        self._pending_note = None             # (wave, f0, ts) consumido por poll_note
        self._last_note = None                # (wave, f0) p/ classify_current

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

    def reload_classifier(self):
        """Recarrega calibração/correções do disco (após calibrar no Treino)."""
        self._classifier = None
        self._load_classifier()

    def has_calibration(self) -> bool:
        return self._classifier is not None

    def calibration_incompatible(self) -> bool:
        """True se existe calibração mas de versão de features antiga."""
        calib = SCRIPT_DIR / "calibration.json"
        if self._classifier is not None or not calib.exists():
            return False
        try:
            from classifier import FretClassifier
            clf = FretClassifier()
            clf.load(calib)
            return clf.incompatible
        except Exception:
            return False

    # ---- metrônomo ----
    @staticmethod
    def _make_clicks(sr: int):
        """Pré-computa 2 cliques curtos (~25ms): normal (1000Hz) e acento (1500Hz)."""
        dur = 0.025
        n = int(sr * dur)
        t = np.arange(n) / sr
        env = np.exp(-t / 0.005)  # tau ~5ms — bem snappy
        normal = (np.sin(2 * np.pi * 1000 * t) * env * 0.6).astype(np.float32)
        accent = (np.sin(2 * np.pi * 1500 * t) * env * 0.85).astype(np.float32)
        return normal, accent

    def _render_metronome(self, outdata, frames):
        if not self.metronome_on or self.metronome_bpm <= 0:
            return
        spb = SAMPLE_RATE * 60.0 / self.metronome_bpm
        block_start = self._metro_sample
        block_end = block_start + frames
        # disparos de beat que caem neste bloco → ativam um click
        k = int(np.ceil(block_start / spb))
        while True:
            beat_pos = int(round(k * spb))
            if beat_pos >= block_end:
                break
            if beat_pos >= block_start:
                is_accent = (self.metronome_accent_every > 0
                             and ((k - self.metronome_beat_offset) % self.metronome_accent_every) == 0)
                click = self._click_accent if is_accent else self._click_normal
                self._active_click = (click, beat_pos)
            k += 1
        # renderiza o click ativo dentro deste bloco
        if self._active_click is not None:
            click, start = self._active_click
            off_block = max(0, start - block_start)
            off_click = max(0, block_start - start)
            n = min(len(click) - off_click, frames - off_block)
            if n > 0:
                mix = click[off_click:off_click + n] * self.metronome_gain
                outdata[off_block:off_block + n, 0] += mix
                outdata[off_block:off_block + n, 1] += mix
                if off_click + n >= len(click):
                    self._active_click = None

    def set_metronome(self, on: bool, bpm: int | None = None,
                      accent_every: int | None = None, gain: float | None = None,
                      beat_offset: int | None = None):
        if bpm is not None:
            self.metronome_bpm = max(20, min(300, int(bpm)))
        if accent_every is not None:
            self.metronome_accent_every = max(0, int(accent_every))
        if gain is not None:
            self.metronome_gain = max(0.0, min(1.5, gain))
        if beat_offset is not None:
            self.metronome_beat_offset = int(beat_offset)
        if on != self.metronome_on:
            self.metronome_on = on
            self._metro_sample = 0
            self._active_click = None
            self._reopen()   # pode precisar abrir/fechar full-duplex

    # ---- ciclo de vida ----
    def start(self):
        if self.device is None:
            raise RuntimeError("Nenhum dispositivo de entrada encontrado (use device=N).")
        self._running = True
        if self.monitor_on or self.metronome_on:
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
                self.output_device = out
                return
            except Exception as e:
                last_err = e
        self.monitor_available = False
        self.monitor_on = False
        self.metronome_on = False   # full-duplex falhou → metrônomo tb não toca
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
        if self.monitor_on or self.metronome_on:
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
        gained = (mono * self.gain).astype(np.float32)
        self.buffer = np.concatenate([self.buffer[len(gained):], gained])
        rms = float(np.sqrt(np.mean(self.buffer * self.buffer)))
        with self._lock:
            self._cur_rms = rms

        # captura da nota em andamento (continua mesmo no silêncio — capta o decay)
        if self._note_capturing:
            self._note_chunks.append(gained.copy())
            self._note_collected += len(gained)
            if self._note_collected >= self._note_target:
                wave = np.concatenate(self._note_chunks)[:self._note_target]
                # recalcula f0 da nota inteira (mais representativo que o do onset)
                f0 = yin(wave, SAMPLE_RATE)
                if f0 < MIN_FREQ or f0 > MAX_FREQ:
                    f0 = self._note_f0
                with self._lock:
                    self._pending_note = (wave, f0, self._note_ts)
                    self._last_note = (wave, f0)
                self._note_capturing = False

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

        # ataque novo
        if self._armed and rms >= self.attack_rms:
            self._armed = False
            ts_now = time.time()   # mesmo timestamp p/ onset e nota
            with self._lock:
                self._pending_onset = (midi, ts_now)
            if not self._note_capturing:   # inicia captura da nota
                self._note_capturing = True
                self._note_chunks = [gained.copy()]
                self._note_collected = len(gained)
                self._note_f0 = freq
                self._note_ts = ts_now

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
            mono = indata[:, 0] * self.monitor_gain
            outdata[:, 0] = mono
            outdata[:, 1] = mono
        else:
            outdata.fill(0)
        # metrônomo (somado ao monitor); avança contador só quando ligado
        if self.metronome_on:
            self._render_metronome(outdata, frames)
            self._metro_sample += frames
        # evita estouro na soma monitor + click
        np.clip(outdata, -1.0, 1.0, out=outdata)

    # ---- API ----
    def poll_onset(self):
        with self._lock:
            onset = self._pending_onset
            self._pending_onset = None
        return onset

    def poll_note(self):
        """Retorna a última nota completa (wave, f0, ts) capturada, ou None."""
        with self._lock:
            note = self._pending_note
            self._pending_note = None
        return note

    def current_pitch(self):
        with self._lock:
            return self._cur_midi, self._cur_freq

    def current_rms(self) -> float:
        with self._lock:
            return self._cur_rms

    def _sustain_threshold(self, clf) -> float:
        """Limiar de sustain p/ separar solta de pressionada — calibrado se houver dados."""
        from features import IDX_SUSTAIN
        if clf is None:
            return DEFAULT_SUSTAIN_THRESHOLD
        opens, frets = [], []
        for (s, f), vecs in clf.samples.items():
            for v in vecs:
                (opens if f == 0 else frets).append(float(v[IDX_SUSTAIN]))
        if opens and frets:
            return (float(np.median(opens)) + float(np.median(frets))) / 2.0
        return DEFAULT_SUSTAIN_THRESHOLD

    def analyze_note(self, note_wave: np.ndarray, f0: float, tuning_name: str) -> dict:
        """Analisa uma nota completa: features, solta/pressionada e ranking de corda/casa."""
        from features import extract_features, IDX_SUSTAIN
        clf = self._classifier   # snapshot (defensivo)
        feats = extract_features(note_wave, SAMPLE_RATE, f0)
        midi = int(round(freq_to_midi(f0)))
        sustain = float(feats[IDX_SUSTAIN])
        thr = self._sustain_threshold(clf)
        is_open = sustain > thr
        open_conf = float(min(1.0, abs(sustain - thr) / (thr + 1e-6)))

        if clf is not None:
            ranking = clf.classify(feats, midi, tuning_name, open_hint=is_open)
        else:
            pos = fret_positions(midi, TUNINGS[tuning_name])
            if pos:
                s, f = min(pos, key=lambda sf: (sf[1], sf[0]))
                ranking = [(s, f, None)]
            else:
                ranking = []
        return {"midi": midi, "features": feats, "is_open": is_open,
                "open_conf": open_conf, "ranking": ranking}

    def classify_current(self, tuning_name: str):
        """Dica de corda/casa pra última nota completa. (s,f,conf) | None.
        Retorna None até uma nota completar (sem fallback degradado de buffer curto)."""
        with self._lock:
            ln = self._last_note
        if ln is None:
            return None
        res = self.analyze_note(ln[0], ln[1], tuning_name)
        r = res["ranking"]
        return r[0] if r else None


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
