"""Sequências de notas ("músicas") para o jogo.

Cada Chart é uma lista de notas com (beat, midi). O tempo real de cada nota é
beat * 60 / bpm segundos a partir do início. midi usa o padrão A4 = 69 = 440 Hz.
"""
from dataclasses import dataclass, field

from fret_detector import note_to_midi


@dataclass
class Note:
    beat: float   # posição em batidas
    midi: int     # nota (número MIDI)


@dataclass
class Chart:
    name: str
    bpm: int
    tuning: str
    notes: list[Note] = field(default_factory=list)
    category: str = "musica"   # "musica" | "teste"

    def duration_beats(self) -> float:
        return max((n.beat for n in self.notes), default=0.0) + 4.0


def _seq(notes_str: str, start_beat: float = 0.0, step: float = 1.0) -> list[Note]:
    """Constrói notas igualmente espaçadas a partir de nomes ('E2 A2 D3 ...')."""
    out = []
    beat = start_beat
    for token in notes_str.split():
        out.append(Note(beat=beat, midi=note_to_midi(token)))
        beat += step
    return out


def _from_midis(midis: list[int], step: float = 1.0) -> list[Note]:
    """Notas igualmente espaçadas a partir de uma lista de MIDI (1 nota por 'step' batidas)."""
    return [Note(beat=i * step, midi=m) for i, m in enumerate(midis)]


# ---- Chart 1: escala / cordas soltas e casas baixas, lento (aprender) ----
ESCALA_MI = Chart(
    name="Escala de Mi (lento)",
    bpm=70,
    tuning="standard",
    notes=_seq(
        # 6ª→1ª soltas, depois desce — sequência simples e reconhecível
        "E2 A2 D3 G3 B3 E4 B3 G3 D3 A2 E2",
        step=2.0,  # uma nota a cada 2 batidas (bem espaçado)
    ),
)

# ---- Chart 2: riff monofônico simples em casas baixas ----
# Melodia fácil (graus de Mi menor pentatônica em região grave/média)
RIFF_SIMPLES = Chart(
    name="Riff Simples",
    bpm=90,
    tuning="standard",
    notes=(
        _seq("E2 G2 A2 E2", start_beat=0.0, step=1.0)
        + _seq("A2 G2 E2", start_beat=4.0, step=1.0)
        + _seq("E2 G2 A2 B2 A2 G2 E2", start_beat=8.0, step=1.0)
    ),
)

# ---- Categoria TESTE: riffs pequenos e LENTOS p/ validar a lógica das notas
# e continuar calibrando a guitarra. Afinação padrão (standard).
# Riff 1: transcrito da tab enviada (gallop na 5ª corda + baixos e B3 na 4ª).
# Lido em afinação PADRÃO — note que a tab original é em Drop D; aqui o objetivo
# é validar a sequência de notas, não a fidelidade musical.
_TESTE_RIFF1_MIDIS = [
    52, 55, 54, 55, 59, 55, 54, 55, 52, 55, 54, 55, 59, 55, 54, 55,
    50, 55, 54, 55, 59, 55, 54, 55, 49, 55, 54, 55, 59, 55, 54, 55,
    52, 55, 54, 55, 59, 55, 54, 55, 52, 55, 54, 55, 59, 55, 54, 55,
    50, 55, 54, 55, 59, 55, 54, 55, 49, 55, 54, 55, 59, 55, 54, 55,
    52, 55, 54, 55, 59, 55, 52, 55, 54, 55, 59, 55, 54, 55, 50, 55,
    54, 55, 59, 55, 54, 55,
]
TESTE_RIFF1 = Chart(
    name="Teste — Riff 1 (lento)",
    bpm=60,
    tuning="standard",
    category="teste",
    notes=_from_midis(_TESTE_RIFF1_MIDIS, step=1.0),  # 1 nota por segundo @ 60 BPM
)

CHARTS: dict[str, Chart] = {
    "escala_mi": ESCALA_MI,
    "riff_simples": RIFF_SIMPLES,
    "teste_riff1": TESTE_RIFF1,
}

DEFAULT_CHART = "escala_mi"
