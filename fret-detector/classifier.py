"""Classificador (corda, casa) baseado em features de timbre.

Usa k-NN com distância euclidiana normalizada (z-score). Carrega samples de
calibração + correções online. Persiste em JSON.

Workflow:
    clf = FretClassifier()
    clf.load("calibration.json", "corrections.json")
    ranked = clf.classify(features, midi_note, "standard")
    # ranked = [(string, fret, confidence), ...]  ordenado por confiança
    clf.learn_correction(features, midi_note, correct_string, correct_fret)
    clf.save_corrections("corrections.json")
"""
import json
import time
from collections import defaultdict
from pathlib import Path
import numpy as np

from features import N_FEATURES
from fret_detector import TUNINGS, note_to_midi, fret_positions, MAX_FRET

MAX_CORRECTIONS = 100
CORRECTION_WEIGHT = 2.0  # cada correção vale 2x um sample de calibração


def key(string: int, fret: int) -> str:
    return f"{string}:{fret}"


def parse_key(k: str) -> tuple[int, int]:
    s, f = k.split(":")
    return int(s), int(f)


class FretClassifier:
    def __init__(self):
        # samples[(string, fret)] = list of feature vectors
        self.samples: dict[tuple[int, int], list[np.ndarray]] = defaultdict(list)
        # samples vindas de correção (peso maior)
        self.corrections: list[dict] = []  # {ts, string, fret, midi, features}
        self.tuning_name: str = "standard"
        self.feature_means: np.ndarray | None = None
        self.feature_stds: np.ndarray | None = None

    def load(self, calib_path: str | Path, corrections_path: str | Path | None = None) -> bool:
        """Carrega calibração + correções. Retorna True se calibração foi carregada."""
        calib_path = Path(calib_path)
        if not calib_path.exists():
            return False
        with open(calib_path, encoding="utf-8") as f:
            data = json.load(f)
        self.tuning_name = data.get("tuning", "standard")
        for k, payload in data.get("samples", {}).items():
            s, fr = parse_key(k)
            for vec in payload.get("vectors", []):
                self.samples[(s, fr)].append(np.array(vec, dtype=np.float32))

        if corrections_path:
            cp = Path(corrections_path)
            if cp.exists():
                with open(cp, encoding="utf-8") as f:
                    self.corrections = json.load(f).get("corrections", [])

        self._recompute_norm()
        return True

    def save_calibration(self, path: str | Path) -> None:
        path = Path(path)
        payload = {
            "tuning": self.tuning_name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "samples": {
                key(s, fr): {"vectors": [v.tolist() for v in vecs], "n": len(vecs)}
                for (s, fr), vecs in self.samples.items()
            },
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save_corrections(self, path: str | Path) -> None:
        path = Path(path)
        payload = {"corrections": self.corrections[-MAX_CORRECTIONS:]}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_calibration_sample(self, string: int, fret: int, features: np.ndarray) -> None:
        self.samples[(string, fret)].append(np.array(features, dtype=np.float32))
        self._recompute_norm()

    def n_calibrated_positions(self) -> int:
        return sum(1 for v in self.samples.values() if v)

    def n_total_labels(self) -> int:
        """Posições únicas com qualquer dado (calibração ou correção)."""
        labels = set(self.samples.keys())
        labels.update((c["string"], c["fret"]) for c in self.corrections)
        return len(labels)

    def _samples_on_string(self, target_string: int) -> list[tuple[int, np.ndarray]]:
        """Retorna [(fret, vetor_medio)] combinando calibração + correções da corda."""
        bucket: dict[int, list[np.ndarray]] = defaultdict(list)
        for (s, f), vecs in self.samples.items():
            if s == target_string:
                bucket[f].extend(vecs)
        for c in self.corrections:
            if c["string"] == target_string:
                bucket[c["fret"]].append(np.array(c["features"], dtype=np.float32))
        return [(f, np.mean(np.stack(vs), axis=0)) for f, vs in bucket.items() if vs]

    def _all_training_set(self) -> list[tuple[tuple[int, int], np.ndarray, float]]:
        """Retorna [(label, vector, weight), ...] juntando calibração + correções."""
        out = []
        for label, vecs in self.samples.items():
            for v in vecs:
                out.append((label, v, 1.0))
        for c in self.corrections:
            label = (c["string"], c["fret"])
            v = np.array(c["features"], dtype=np.float32)
            out.append((label, v, CORRECTION_WEIGHT))
        return out

    def _recompute_norm(self) -> None:
        """Calcula média e desvio padrão por feature pra normalizar distância."""
        all_vecs = [v for _, v, _ in self._all_training_set()]
        if not all_vecs:
            self.feature_means = np.zeros(N_FEATURES, dtype=np.float32)
            self.feature_stds = np.ones(N_FEATURES, dtype=np.float32)
            return
        arr = np.stack(all_vecs)
        self.feature_means = arr.mean(axis=0)
        self.feature_stds = arr.std(axis=0)
        self.feature_stds[self.feature_stds < 1e-6] = 1.0

    def _normalize(self, v: np.ndarray) -> np.ndarray:
        return (v - self.feature_means) / self.feature_stds

    def _nearest_calibrated(self, target_string: int, target_fret: int) -> np.ndarray | None:
        """Acha o vetor de features médio para a posição mais próxima calibrada
        naquela corda. Se a casa exata existe, usa ela; senão interpola entre as
        2 mais próximas (linear nas features). Considera calibração + correções."""
        on_string = self._samples_on_string(target_string)
        if not on_string:
            return None
        on_string.sort(key=lambda x: x[0])
        # match exato
        for fret, vec in on_string:
            if fret == target_fret:
                return vec
        # interpola entre vizinhos
        below = [(f, v) for f, v in on_string if f < target_fret]
        above = [(f, v) for f, v in on_string if f > target_fret]
        if below and above:
            f_low, v_low = below[-1]
            f_hi, v_hi = above[0]
            t = (target_fret - f_low) / (f_hi - f_low)
            return (1 - t) * v_low + t * v_hi
        # extrapolação simples: usa o mais próximo
        if below:
            return below[-1][1]
        return above[0][1]

    @staticmethod
    def _ergonomic_prior(fret: int) -> float:
        """Plausibilidade de tocar nesta casa. Casas baixas são muito mais comuns;
        casa 19 na 6ª corda é rara. Suave: 1.0 na solta → ~0.39 na casa 19."""
        return 1.0 / (1.0 + fret / 12.0)

    def classify(
        self,
        features: np.ndarray,
        midi_note: int,
        tuning_name: str | None = None,
        ergonomic_weight: float = 1.0,
    ) -> list[tuple[int, int, float]]:
        """Retorna lista ordenada [(string, fret, confidence)].

        ergonomic_weight: 0 = só timbre; 1 = aplica viés de ergonomia (default).
        O viés penaliza casas altas (posições fisicamente improváveis)."""
        tuning = TUNINGS[tuning_name or self.tuning_name]
        candidates = fret_positions(midi_note, tuning)
        if not candidates:
            return []

        if self.n_total_labels() == 0:
            # Nenhum dado: heurística simples — preferir casas baixas
            scored = [(s, f, 1.0 / (1.0 + f * 0.3)) for s, f in candidates]
            total = sum(c for _, _, c in scored)
            return sorted(
                [(s, f, c / total) for s, f, c in scored],
                key=lambda x: -x[2],
            )

        feat_norm = self._normalize(features)
        scored = []
        for s, f in candidates:
            ref = self._nearest_calibrated(s, f)
            if ref is None:
                # corda não calibrada: distância "infinita" → conf baixa
                scored.append((s, f, 1e6))
                continue
            ref_norm = self._normalize(ref)
            dist = float(np.linalg.norm(feat_norm - ref_norm))
            scored.append((s, f, dist))

        # converte distância em confiança via softmax inversa
        dists = np.array([d for _, _, d in scored])
        rel = dists - dists.min()
        weights = np.exp(-rel)

        # viés de ergonomia: multiplica peso pela plausibilidade da casa
        if ergonomic_weight > 0:
            priors = np.array([self._ergonomic_prior(f) ** ergonomic_weight
                               for _, f, _ in scored])
            weights = weights * priors

        confidences = weights / weights.sum()

        out = [(s, f, float(conf)) for (s, f, _), conf in zip(scored, confidences)]
        out.sort(key=lambda x: -x[2])
        return out

    def learn_correction(
        self,
        features: np.ndarray,
        midi_note: int,
        correct_string: int,
        correct_fret: int,
    ) -> None:
        """Registra que features+midi devem ter sido classificadas como (corda, casa).
        Adiciona à fila de correções (peso 2x); refaz normalização."""
        self.corrections.append({
            "ts": time.time(),
            "string": int(correct_string),
            "fret": int(correct_fret),
            "midi": int(midi_note),
            "features": [float(x) for x in features],
        })
        # mantém só as últimas MAX_CORRECTIONS
        self.corrections = self.corrections[-MAX_CORRECTIONS:]
        self._recompute_norm()
