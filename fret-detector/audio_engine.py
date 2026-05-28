"""Motor de áudio para o jogo: captura em thread, detecta pitch (YIN) e ataques (onset).

O game loop chama poll_onset() a cada frame: retorna (midi, timestamp) quando um
novo ATAQUE foi tocado, ou None. Isso evita que uma nota sustentada conte como
vários acertos — só o ataque (pluck) dispara um evento.

Uso:
    eng = AudioEngine(device=2, gain=40)
    eng.start()
    ...
    onset = eng.poll_onset()      # (midi, ts) ou None
    midi, freq = eng.current_pitch()
    eng.stop()
"""
import threading
import time
import numpy as np
import sounddevice as sd

from fret_detector import (
    SAMPLE_RATE, HOP_SIZE, MIN_FREQ, MAX_FREQ,
    yin, freq_to_midi, find_tank_g_device,
)

BUFFER_SIZE = 2048  # ~46 ms — menor latência que o tuner, melhor pra ritmo


class AudioEngine:
    def __init__(self, device=None, gain=40.0,
                 silence_rms=0.004, attack_rms=0.015):
        """
        silence_rms: abaixo disso = silêncio (rearma o detector de ataque)
        attack_rms:  acima disso (estando armado) = novo ataque
        """
        self.device = device if device is not None else find_tank_g_device()
        self.gain = gain
        self.silence_rms = silence_rms
        self.attack_rms = attack_rms

        self.buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
        self._lock = threading.Lock()
        self._running = False
        self.stream = None

        # estado de pitch contínuo
        self._cur_midi = None
        self._cur_freq = 0.0

        # detector de onset (máquina de 2 estados)
        self._armed = True              # pronto pra disparar
        self._pending_onset = None      # (midi, ts) ainda não consumido pelo jogo

    # ---- ciclo de vida ----
    def start(self):
        if self.device is None:
            raise RuntimeError("Nenhum dispositivo de entrada encontrado (use device=N).")
        self._running = True
        self.stream = sd.InputStream(
            device=self.device, samplerate=SAMPLE_RATE, channels=1,
            blocksize=HOP_SIZE, callback=self._callback,
        )
        self.stream.start()

    def stop(self):
        self._running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
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

    # ---- callback de áudio (thread do sounddevice) ----
    def _callback(self, indata, frames, time_info, status):
        if not self._running:
            return
        new_audio = indata[:, 0] * self.gain
        self.buffer = np.concatenate([self.buffer[len(new_audio):], new_audio])

        rms = float(np.sqrt(np.mean(self.buffer * self.buffer)))

        # rearma quando volta ao silêncio
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

        # dispara ataque na subida de energia, se estava armado
        if self._armed and rms >= self.attack_rms:
            self._armed = False
            with self._lock:
                self._pending_onset = (midi, time.time())

    # ---- API consumida pelo jogo ----
    def poll_onset(self):
        """Retorna (midi, ts) de um novo ataque, ou None. Consome o evento."""
        with self._lock:
            onset = self._pending_onset
            self._pending_onset = None
        return onset

    def current_pitch(self):
        with self._lock:
            return self._cur_midi, self._cur_freq


# ---- detector de onset reutilizável p/ testes offline (sem sounddevice) ----
class OnsetDetector:
    """Mesma lógica de onset do AudioEngine, mas alimentada manualmente —
    permite testar com buffers sintéticos sem hardware."""
    def __init__(self, silence_rms=0.004, attack_rms=0.015):
        self.silence_rms = silence_rms
        self.attack_rms = attack_rms
        self.buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
        self._armed = True

    def push(self, block: np.ndarray, ts: float):
        """Empurra um bloco de áudio. Retorna (midi, ts) se houve ataque, senão None."""
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
