"""Extração de features de timbre para classificar corda/casa e solta/pressionada.

Recebe a NOTA INTEIRA (~0.5s a partir do onset) + o f0 (já detectado pelo YIN)
e retorna 8 features. Combina features espectrais (sobre uma janela estável) e
temporais (envelope da nota inteira). Tudo numpy puro.

Versão do conjunto: FEATURE_SET. Mudou em relação à v1 (6 features) — calibrações
antigas ficam incompatíveis (o classifier detecta pela contagem/versão).
"""
import numpy as np

FEATURE_SET = "v2"

FEATURE_NAMES = (
    "brightness_index",       # energia (2-4kHz)/(500-1k) dB  — qual corda
    "spectral_tilt",          # slope log-log do espectro       — corda grossa/fina
    "centroid_normalized",    # centroid / f0                   — corda, invariante a pitch
    "inharmonicity_b",        # coef. B robusto (h1-h5 + IQR)   — corda + solta/fretted
    "harmonic_richness",      # nº harmônicos > 10% do f0       — solta/fretted + corda
    "harmonic_decay_rate",    # média h_n/h_(n+1)               — solta/fretted
    "sustain_ratio",          # energia(tardia)/energia(ataque) — SOLTA vs fretted (chave)
    "attack_energy_ratio",    # energia(ataque)/energia total   — solta/fretted
)
N_FEATURES = len(FEATURE_NAMES)

# pesos por feature p/ k-NN ponderado (discriminadores fortes pesam mais)
FEATURE_WEIGHTS = np.array([1.4, 1.3, 1.0, 1.2, 1.0, 1.1, 1.5, 1.1], dtype=np.float32)

_SPEC_N = 4096   # janela do espectro (resolução ~10.8 Hz @ 44.1k)


# ----------------------------- espectro -----------------------------
def _stable_window(note_wave: np.ndarray, sr: int, n: int = _SPEC_N) -> np.ndarray:
    """Janela estável (pula o transiente inicial) p/ análise espectral."""
    start = min(int(0.03 * sr), max(0, len(note_wave) - n))
    win = note_wave[start:start + n]
    if len(win) < n:
        win = np.pad(win, (0, n - len(win)))
    return win


def _spectrum(window: np.ndarray, sr: int):
    w = np.hanning(len(window))
    spec = np.abs(np.fft.rfft(window * w))
    freqs = np.fft.rfftfreq(len(window), 1 / sr)
    return freqs, spec


def _peak_near(freqs, spec, target_hz, search_pct=0.04):
    if target_hz <= 0 or target_hz >= freqs[-1]:
        return target_hz, 0.0
    bw = target_hz * search_pct
    mask = (freqs >= target_hz - bw) & (freqs <= target_hz + bw)
    if not mask.any():
        return target_hz, 0.0
    sub_spec = spec[mask]
    sub_freq = freqs[mask]
    i = int(np.argmax(sub_spec))
    return float(sub_freq[i]), float(sub_spec[i])


# ----------------------------- features espectrais -----------------------------
def _brightness_index(freqs, spec):
    bright = spec[(freqs >= 2000) & (freqs <= 4000)].sum()
    warm = spec[(freqs >= 500) & (freqs <= 1000)].sum()
    return float(20 * np.log10((bright + 1e-9) / (warm + 1e-9)))


def _spectral_tilt(freqs, spec, f0):
    lo = max(2 * f0, 100.0)
    mask = (freqs > lo) & (spec > 0)
    if mask.sum() < 4:
        return 0.0
    log_f = np.log(freqs[mask])
    log_s = np.log(spec[mask] + 1e-12)
    slope = np.polyfit(log_f, log_s, 1)[0]
    return float(slope)


def _centroid_normalized(freqs, spec, f0):
    total = spec.sum()
    if total < 1e-12 or f0 <= 0:
        return 0.0
    centroid = float((freqs * spec).sum() / total)
    return centroid / f0


def _inharmonicity_robust(freqs, spec, f0, n_harmonics=5):
    ns, ys = [], []
    for n in range(1, n_harmonics + 1):
        f_real, mag = _peak_near(freqs, spec, n * f0)
        if mag < 1e-9 or f_real <= 0:
            continue
        ns.append(float(n * n))
        ys.append((f_real / (n * f0)) ** 2 - 1.0)
    if len(ns) < 2:
        return 0.0
    ns = np.array(ns)
    ys = np.array(ys)
    if len(ys) >= 4:  # remoção de outliers por IQR
        q1, q3 = np.percentile(ys, [25, 75])
        iqr = q3 - q1
        keep = (ys >= q1 - 1.5 * iqr) & (ys <= q3 + 1.5 * iqr)
        if keep.sum() >= 2:
            ns, ys = ns[keep], ys[keep]
    denom = float((ns * ns).sum())
    if denom < 1e-12:
        return 0.0
    return float((ns * ys).sum() / denom)


def _harmonic_richness(freqs, spec, f0):
    _, mag_h1 = _peak_near(freqs, spec, f0)
    if mag_h1 < 1e-9:
        return 0.0
    thr = 0.1 * mag_h1
    count = 0
    for n in range(1, 16):
        if n * f0 >= freqs[-1]:
            break
        _, mag = _peak_near(freqs, spec, n * f0)
        if mag >= thr:
            count += 1
    return float(count)


def _harmonic_decay_rate(freqs, spec, f0):
    amps = []
    for n in range(1, 9):
        _, mag = _peak_near(freqs, spec, n * f0)
        amps.append(max(mag, 1e-9))
    # razão entre harmônicos consecutivos, clipada p/ não explodir em harmônico ausente
    ratios = [min(10.0, max(0.1, amps[i] / amps[i + 1])) for i in range(len(amps) - 1)]
    return float(np.median(ratios)) if ratios else 1.0


# ----------------------------- features temporais -----------------------------
def _energy(seg):
    return float(np.sum(seg.astype(np.float64) ** 2))


def _sustain_ratio(note_wave, sr):
    """energia(tardia 0.3-0.5s) / energia(ataque 0-0.15s). Solta → maior."""
    n = len(note_wave)
    early = note_wave[:min(int(0.15 * sr), n)]
    lo = int(0.3 * sr)
    hi = int(0.5 * sr)
    if hi > n:  # nota curta: usa a metade final como "tardia"
        lo, hi = int(0.6 * n), n
    late = note_wave[lo:hi]
    e_early = _energy(early)
    e_late = _energy(late)
    if e_early < 1e-12:
        return 0.0
    return float(e_late / e_early)


def _attack_energy_ratio(note_wave, sr):
    n = len(note_wave)
    transient = note_wave[:min(int(0.1 * sr), n)]
    e_t = _energy(transient)
    e_total = _energy(note_wave)
    if e_total < 1e-12:
        return 0.0
    return float(e_t / e_total)


# ----------------------------- API -----------------------------
def extract_features(note_wave: np.ndarray, sr: int, f0: float) -> np.ndarray:
    """Vetor de N_FEATURES floats. `note_wave` deve ser a nota inteira (~0.5s);
    `f0` vem do YIN. Se f0<=0 ou wave muito curto, retorna zeros."""
    note_wave = np.asarray(note_wave, dtype=np.float32)
    if f0 <= 0 or len(note_wave) < 256:
        return np.zeros(N_FEATURES, dtype=np.float32)

    win = _stable_window(note_wave, sr)
    freqs, spec = _spectrum(win, sr)

    return np.array([
        _brightness_index(freqs, spec),
        _spectral_tilt(freqs, spec, f0),
        _centroid_normalized(freqs, spec, f0),
        _inharmonicity_robust(freqs, spec, f0),
        _harmonic_richness(freqs, spec, f0),
        _harmonic_decay_rate(freqs, spec, f0),
        _sustain_ratio(note_wave, sr),
        _attack_energy_ratio(note_wave, sr),
    ], dtype=np.float32)


def features_dict(vec: np.ndarray) -> dict[str, float]:
    return {name: float(vec[i]) for i, name in enumerate(FEATURE_NAMES)}


# índices úteis p/ detecção solta/pressionada (usado pelo audio_engine)
IDX_SUSTAIN = FEATURE_NAMES.index("sustain_ratio")
IDX_DECAY = FEATURE_NAMES.index("harmonic_decay_rate")
IDX_ATTACK = FEATURE_NAMES.index("attack_energy_ratio")
