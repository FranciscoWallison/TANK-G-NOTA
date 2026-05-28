"""Extração de features de timbre para classificar corda/casa.

Tudo numpy puro. Recebe buffer de áudio + f0 (já detectado pelo YIN) e retorna
um vetor de floats representando o "timbre" daquela nota.

Features (ordem fixa em FEATURE_NAMES):
    1. spectral_centroid  — Hz; cordas finas têm centroide mais alto
    2. spectral_rolloff85 — Hz; onde 85% da energia espectral está acumulada
    3. zero_crossing_rate — proporção; cordas plain têm ZCR maior
    4. inharmonicity_B    — adimensional; cordas grossas/curtas têm B maior
    5. h1_h2_ratio        — dB; energia do 1º harmônico vs 2º
    6. hi_lo_ratio        — dB; soma harmônicos 4-8 vs 1-3
"""
import numpy as np

FEATURE_NAMES = (
    "spectral_centroid",
    "spectral_rolloff85",
    "zero_crossing_rate",
    "inharmonicity_B",
    "h1_h2_ratio",
    "hi_lo_ratio",
)
N_FEATURES = len(FEATURE_NAMES)


def _spectrum(buffer: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(len(buffer))
    spec = np.abs(np.fft.rfft(buffer * window))
    freqs = np.fft.rfftfreq(len(buffer), 1 / sr)
    return freqs, spec


def _spectral_centroid(freqs: np.ndarray, spec: np.ndarray) -> float:
    total = spec.sum()
    if total < 1e-12:
        return 0.0
    return float((freqs * spec).sum() / total)


def _spectral_rolloff(freqs: np.ndarray, spec: np.ndarray, pct: float = 0.85) -> float:
    cumulative = np.cumsum(spec)
    total = cumulative[-1]
    if total < 1e-12:
        return 0.0
    idx = np.searchsorted(cumulative, pct * total)
    idx = min(idx, len(freqs) - 1)
    return float(freqs[idx])


def _zero_crossing_rate(buffer: np.ndarray) -> float:
    signs = np.sign(buffer)
    signs[signs == 0] = 1
    return float(np.mean(signs[:-1] != signs[1:]))


def _peak_near(freqs: np.ndarray, spec: np.ndarray, target_hz: float, search_pct: float = 0.04) -> tuple[float, float]:
    """Encontra pico do espectro próximo a target_hz. Retorna (freq_real, magnitude)."""
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


def _inharmonicity(freqs: np.ndarray, spec: np.ndarray, f0: float, n_harmonics: int = 5) -> float:
    """Estima coeficiente B onde f_n = n * f0 * sqrt(1 + B * n^2).

    Linearizado: (f_n / (n*f0))^2 - 1 ≈ B * n^2
    Usa só primeiros 5 harmônicos pra robustez com sinal saturado.
    """
    ns = []
    ys = []
    for n in range(1, n_harmonics + 1):
        f_real, mag = _peak_near(freqs, spec, n * f0)
        if mag < 1e-9 or f_real <= 0:
            continue
        ratio = (f_real / (n * f0)) ** 2 - 1.0
        ns.append(n * n)
        ys.append(ratio)
    if len(ns) < 2:
        return 0.0
    ns = np.array(ns, dtype=float)
    ys = np.array(ys, dtype=float)
    # regressão linear pelo origem: B = sum(n^2 * y) / sum(n^4)
    denom = float((ns * ns).sum())
    if denom < 1e-12:
        return 0.0
    return float((ns * ys).sum() / denom)


def _harmonic_ratios(freqs: np.ndarray, spec: np.ndarray, f0: float) -> tuple[float, float]:
    """Retorna (h1/h2 em dB, hi/lo em dB)."""
    mags = []
    for n in range(1, 9):
        _, mag = _peak_near(freqs, spec, n * f0)
        mags.append(mag)
    eps = 1e-9
    h1, h2 = mags[0], mags[1]
    h1_h2 = 20 * np.log10((h1 + eps) / (h2 + eps))
    lo = sum(mags[0:3]) + eps   # h1..h3
    hi = sum(mags[3:8]) + eps   # h4..h8
    hi_lo = 20 * np.log10(hi / lo)
    return float(h1_h2), float(hi_lo)


def extract_features(buffer: np.ndarray, sr: int, f0: float) -> np.ndarray:
    """Vetor de N_FEATURES floats descrevendo o timbre.

    `f0` deve vir do YIN (já calculado upstream). Se f0 <= 0, todas features são 0.
    """
    if f0 <= 0 or len(buffer) < 256:
        return np.zeros(N_FEATURES, dtype=np.float32)

    freqs, spec = _spectrum(buffer, sr)
    centroid = _spectral_centroid(freqs, spec)
    rolloff = _spectral_rolloff(freqs, spec, 0.85)
    zcr = _zero_crossing_rate(buffer)
    inh_b = _inharmonicity(freqs, spec, f0)
    h1_h2, hi_lo = _harmonic_ratios(freqs, spec, f0)

    return np.array([centroid, rolloff, zcr, inh_b, h1_h2, hi_lo], dtype=np.float32)


def features_dict(vec: np.ndarray) -> dict[str, float]:
    """Apenas pra inspeção/debug."""
    return {name: float(vec[i]) for i, name in enumerate(FEATURE_NAMES)}
