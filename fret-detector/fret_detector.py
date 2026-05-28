"""
Fret Detector v1 — detector de nota + posições no braço da guitarra.

Lê áudio do TANK-G (ou qualquer entrada), detecta a nota tocada com YIN,
e mostra todas as casas/cordas possíveis na afinação atual.

Uso:
    python fret_detector.py                  # auto-detecta TANK-G
    python fret_detector.py --device 5       # força ID específico
    python fret_detector.py --tuning drop-b  # outra afinação
    python fret_detector.py --list           # lista afinações suportadas
"""
import argparse
import sys
import time
from pathlib import Path
import numpy as np
import sounddevice as sd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent

SAMPLE_RATE = 44100
BUFFER_SIZE = 2048            # ~46 ms — bom equilíbrio latência/precisão
HOP_SIZE = 1024               # processa a cada 23 ms
YIN_THRESHOLD = 0.15
MIN_FREQ = 70.0               # B1 (~62Hz) é a mais baixa esperada; usa folga
MAX_FREQ = 1500.0             # G6 ~1568Hz cobre solos altos
SILENCE_RMS = 0.001           # abaixo disso considera silêncio (ajustável via --threshold)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

TUNINGS = {
    "standard": ["E2", "A2", "D3", "G3", "B3", "E4"],
    "drop-d":   ["D2", "A2", "D3", "G3", "B3", "E4"],
    "drop-c":   ["C2", "G2", "C3", "F3", "A3", "D4"],
    "drop-b":   ["B1", "F#2", "B2", "E3", "G#3", "C#4"],
    "drop-a":   ["A1", "E2", "A2", "D3", "F#3", "B3"],
    "eb":       ["D#2", "G#2", "C#3", "F#3", "A#3", "D#4"],
}

MAX_FRET = 24


def note_to_midi(note: str) -> int:
    """Converte 'E2' / 'F#3' para número MIDI. C4 = 60."""
    name = note[:-1]
    octave = int(note[-1])
    semitone = NOTE_NAMES.index(name)
    return 12 * (octave + 1) + semitone


def midi_to_note(midi: int) -> str:
    name = NOTE_NAMES[midi % 12]
    octave = midi // 12 - 1
    return f"{name}{octave}"


def freq_to_midi(freq: float) -> float:
    return 69 + 12 * np.log2(freq / 440.0)


def yin(buffer: np.ndarray, sr: int, threshold: float = YIN_THRESHOLD) -> float:
    """YIN pitch detection. Retorna frequência em Hz, ou 0 se não detectou."""
    tau_min = int(sr / MAX_FREQ)
    tau_max = int(sr / MIN_FREQ)
    if tau_max >= len(buffer):
        return 0.0

    # 1. Difference function
    diff = np.zeros(tau_max)
    for tau in range(1, tau_max):
        delta = buffer[: len(buffer) - tau] - buffer[tau : len(buffer)]
        diff[tau] = np.sum(delta * delta)

    # 2. Cumulative mean normalized difference
    cmnd = np.zeros(tau_max)
    cmnd[0] = 1.0
    running = 0.0
    for tau in range(1, tau_max):
        running += diff[tau]
        cmnd[tau] = diff[tau] * tau / running if running > 0 else 1.0

    # 3. Absolute threshold — primeiro tau onde cmnd cai abaixo do threshold
    tau = tau_min
    while tau < tau_max:
        if cmnd[tau] < threshold:
            while tau + 1 < tau_max and cmnd[tau + 1] < cmnd[tau]:
                tau += 1
            break
        tau += 1
    else:
        return 0.0

    # 3b. Correção de oitava — em cordas graves o 2º harmônico às vezes domina e o
    # YIN pega a oitava ACIMA (tau menor = P/2). Verifica múltiplos de tau (períodos
    # mais graves): se o vale em 2*tau (ou 3*tau) for SIGNIFICATIVAMENTE mais profundo
    # que o vale atual, a fundamental real é esse múltiplo. Conservador:
    #  - só age em sinais "reais" (base_cmnd > 0.01); senóide pura tem base≈0 → pula
    #  - exige vale ≥10% mais profundo pra evitar puxar oitava abaixo demais
    #  - para no primeiro múltiplo válido (não desce oitavas em cascata)
    base_cmnd = cmnd[tau]
    if base_cmnd > 0.01:
        for mult in (2, 3):
            cand = tau * mult
            if cand >= tau_max:
                break
            lo = max(tau_min, int(cand * 0.93))
            hi = min(tau_max - 1, int(cand * 1.07))
            if hi <= lo:
                continue
            local = lo + int(np.argmin(cmnd[lo:hi]))
            if cmnd[local] < base_cmnd * 0.9:
                tau = local
                break

    # 4. Refinamento parabólico
    tau_i = int(round(tau))
    if 0 < tau_i < tau_max - 1:
        s0, s1, s2 = cmnd[tau_i - 1], cmnd[tau_i], cmnd[tau_i + 1]
        denom = 2 * (2 * s1 - s2 - s0)
        if denom != 0:
            tau = tau_i + (s2 - s0) / denom

    return sr / tau if tau > 0 else 0.0


def fret_positions(midi_target: int, tuning: list[str]) -> list[tuple[int, int]]:
    """Retorna lista de (corda, casa) tocáveis. Corda 1 = mais aguda (E)."""
    positions = []
    # tuning[0] = corda mais grave (6ª). Inverter para corda 1 = mais aguda.
    for idx, open_note in enumerate(reversed(tuning)):
        open_midi = note_to_midi(open_note)
        fret = midi_target - open_midi
        if 0 <= fret <= MAX_FRET:
            string_num = idx + 1  # 1..6
            positions.append((string_num, fret))
    return positions


def find_tank_g_device() -> int | None:
    """Auto-detecta TANK-G procurando 'USB-Audio' / 'TANK' / 'M-VAVE'."""
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] == 0:
            continue
        name_lower = d["name"].lower()
        if any(k in name_lower for k in ("usb-audio", "tank-g", "tank g", "m-vave", "mvave")):
            return i
    return None


def format_classify_output(
    freq: float, cents: float, tuning_name: str, tuning: list[str],
    note: str, ranking: list[tuple[int, int, float]],
) -> str:
    """Output v2: top-1 destacado + ranking."""
    if not ranking:
        return f"\n   ⚠️  Sem candidatos para {note}\n"
    top_s, top_f, top_c = ranking[0]
    open_note = list(reversed(tuning))[top_s - 1]
    fret_label = "solta" if top_f == 0 else f"casa {top_f}"
    conf_pct = top_c * 100
    single = len(ranking) == 1
    if single:
        conf_str = "única posição"
        conf_indicator = "•"
    else:
        conf_str = f"conf {conf_pct:5.1f}%"
        conf_indicator = "✓" if conf_pct > 60 else ("~" if conf_pct > 35 else "?")
    cents_str = f"{cents:+.0f}¢"

    lines = [
        f"\n╔══════════════════════════════════════════════════════════╗",
        f"║  🎸  Corda {top_s} ({open_note:<3}) {fret_label:<8} → {note:<4}"
        f"  {conf_str:<14} {conf_indicator}  ║",
        f"║      {freq:7.2f} Hz   {cents_str:>6}   afinação: {tuning_name:<10}              ║",
    ]
    others = ranking[1:4]
    if others:
        lines.append("╠══════════════════════════════════════════════════════════╣")
        lines.append("║  Alternativas:                                            ║")
        for s, f, c in others:
            on = list(reversed(tuning))[s - 1]
            fl = "solta" if f == 0 else f"casa {f:2d}"
            lines.append(f"║    Corda {s} ({on:<3}) {fl:<8} → {c * 100:5.1f}%                   ║")
    lines.append("╠══════════════════════════════════════════════════════════╣")
    lines.append("║  [e] errou  [u] desfaz última correção  [q] sair         ║")
    lines.append("╚══════════════════════════════════════════════════════════╝")
    return "\n".join(lines)


def format_output(freq: float, tuning_name: str, tuning: list[str], cents: float) -> str:
    midi_float = freq_to_midi(freq)
    midi = int(round(midi_float))
    note = midi_to_note(midi)
    positions = fret_positions(midi, tuning)

    cents_str = f"{cents:+.0f}¢"
    tune_indicator = "✓" if abs(cents) < 10 else ("♭" if cents < 0 else "♯")

    lines = [
        f"\n╔══════════════════════════════════════════════════════════╗",
        f"║  Nota: {note:<6} {freq:7.2f} Hz   {tune_indicator} {cents_str:>6}   afinação: {tuning_name:<10} ║",
        f"╠══════════════════════════════════════════════════════════╣",
    ]
    if positions:
        for string, fret in positions:
            open_note = list(reversed(tuning))[string - 1]
            bar_len = min(fret, 24)
            bar = "·" * bar_len + "●" + "·" * (24 - bar_len)
            fret_label = f"casa {fret:2d}" if fret > 0 else "  solta"
            lines.append(f"║  {string}ª ({open_note:<3}) {fret_label}  |{bar}|        ║")
    else:
        lines.append(f"║  (nota fora do alcance da afinação)                      ║")
    lines.append(f"╚══════════════════════════════════════════════════════════╝")
    return "\n".join(lines)


def _try_kbhit():
    """Retorna tecla pressionada (lower) ou None. Windows-friendly via msvcrt."""
    try:
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getwch().lower()
    except ImportError:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, help="ID do dispositivo de entrada")
    parser.add_argument("--tuning", default="standard", choices=list(TUNINGS.keys()))
    parser.add_argument("--list", action="store_true", help="Lista afinações e sai")
    parser.add_argument("--threshold", type=float, default=SILENCE_RMS,
                        help=f"Limiar RMS de silêncio (default {SILENCE_RMS}, menor = mais sensível)")
    parser.add_argument("--gain", type=float, default=1.0,
                        help="Multiplicador de ganho aplicado ao buffer (default 1.0). Use 5–20 se sinal fraco.")
    parser.add_argument("--classify", action="store_true",
                        help="Modo v2: usa calibração para adivinhar corda+casa.")
    parser.add_argument("--calibration", default=str(SCRIPT_DIR / "calibration.json"),
                        help="Caminho do JSON de calibração (default: na pasta do script)")
    parser.add_argument("--corrections", default=str(SCRIPT_DIR / "corrections.json"),
                        help="Caminho do JSON de correções (default: na pasta do script)")
    args = parser.parse_args()

    if args.list:
        print("Afinações suportadas:")
        for name, notes in TUNINGS.items():
            print(f"  {name:<10} → {' '.join(notes)}")
        return

    tuning = TUNINGS[args.tuning]

    if args.device is None:
        device = find_tank_g_device()
        if device is None:
            print("⚠️  TANK-G não encontrado. Usando dispositivo padrão.")
            print("    Para forçar, rode: python list_devices.py")
            device = sd.default.device[0]
    else:
        device = args.device

    info = sd.query_devices(device)
    print(f"🎸 Capturando de: [{device}] {info['name']}")
    print(f"🎵 Afinação:      {args.tuning} ({' '.join(tuning)})")

    classifier = None
    if args.classify:
        from features import extract_features
        from classifier import FretClassifier
        classifier = FretClassifier()
        loaded = classifier.load(args.calibration, args.corrections)
        if not loaded:
            print(f"\n⚠️  Calibração '{args.calibration}' não encontrada.")
            print(f"    Rode primeiro:  python calibrate.py --device {device} --gain {args.gain} --tuning {args.tuning}")
            print(f"    Vou continuar em modo heurístico (precisão ~55%).")
        else:
            print(f"📂 Calibração carregada: {classifier.n_calibrated_positions()} posições"
                  f" + {len(classifier.corrections)} correções")
        print("   Modo: 🧠 CLASSIFY (top-1 + ranking)")
    print("   Toque uma nota (Ctrl+C ou 'q' para sair)\n")

    buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
    last_note_print = ""
    last_print_time = 0.0
    # Estado pra "errou" — guarda última detecção pra poder corrigir
    last_state = {"features": None, "midi": None, "ranking": None, "rank_idx": 0}

    def callback(indata, frames, time_info, status):
        nonlocal buffer, last_note_print, last_print_time
        if status:
            pass  # silencia overflows na saída — não polui o terminal

        new_audio = indata[:, 0] * args.gain
        buffer = np.concatenate([buffer[len(new_audio):], new_audio])

        rms = np.sqrt(np.mean(buffer * buffer))
        if rms < args.threshold:
            return

        freq = yin(buffer, SAMPLE_RATE)
        if freq < MIN_FREQ or freq > MAX_FREQ:
            return

        midi_float = freq_to_midi(freq)
        midi = int(round(midi_float))
        cents = (midi_float - midi) * 100
        note = midi_to_note(midi)

        now = time.time()
        if note == last_note_print and (now - last_print_time) < 0.5:
            return
        last_note_print = note
        last_print_time = now

        if classifier is not None:
            feats = extract_features(buffer.copy(), SAMPLE_RATE, freq)
            ranking = classifier.classify(feats, midi, args.tuning)
            last_state["features"] = feats
            last_state["midi"] = midi
            last_state["ranking"] = ranking
            last_state["rank_idx"] = 0
            print(format_classify_output(freq, cents, args.tuning, tuning, note, ranking))
        else:
            print(format_output(freq, args.tuning, tuning, cents))

    try:
        with sd.InputStream(
            device=device,
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=HOP_SIZE,
            callback=callback,
        ):
            while True:
                key = _try_kbhit()
                if key == "q":
                    print("\n👋 Encerrado.")
                    break
                if key == "e" and classifier is not None and last_state["ranking"]:
                    last_state["rank_idx"] += 1
                    if last_state["rank_idx"] >= len(last_state["ranking"]):
                        print("\n⚠️  Já tentei todas as alternativas — ignorando.")
                        last_state["rank_idx"] = len(last_state["ranking"]) - 1
                        continue
                    s, f, _ = last_state["ranking"][last_state["rank_idx"]]
                    classifier.learn_correction(
                        last_state["features"], last_state["midi"], s, f
                    )
                    classifier.save_corrections(args.corrections)
                    open_note = list(reversed(tuning))[s - 1]
                    fl = "solta" if f == 0 else f"casa {f}"
                    print(f"\n✏️  Aprendi: era corda {s} ({open_note}) {fl}. "
                          f"({len(classifier.corrections)} correções acumuladas)")
                if key == "u" and classifier is not None and classifier.corrections:
                    removed = classifier.corrections.pop()
                    classifier._recompute_norm()
                    classifier.save_corrections(args.corrections)
                    print(f"\n↶  Desfeito: corda {removed['string']} casa {removed['fret']}")
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n👋 Encerrado.")


if __name__ == "__main__":
    main()
