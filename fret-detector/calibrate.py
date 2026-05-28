"""Calibração interativa do TANK-G — guia o usuário a tocar cada (corda, casa)
e salva calibration.json para o classificador.

Uso típico:
    python calibrate.py --device 2 --gain 20 --tuning standard

Flags opcionais:
    --frets 0,5,7,12,17    casas a amostrar (default 0,5,7,12)
    --samples 2            amostras por posição (default 2)
    --resume               retoma calibração existente sem zerar
    --output calibration.json   caminho de saída
"""
import argparse
import sys
import time
from pathlib import Path
import numpy as np
import sounddevice as sd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fret_detector import (
    SAMPLE_RATE, BUFFER_SIZE, TUNINGS, yin, freq_to_midi, midi_to_note,
    note_to_midi, find_tank_g_device,
)
from features import extract_features
from classifier import FretClassifier

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_FRETS = (0, 5, 7, 12)
CAPTURE_SECONDS = 2.5  # tempo de gravação por amostra (folga pra tocar após o ENTER)

STRING_NAMES = {1: "1ª (mais aguda)", 2: "2ª", 3: "3ª", 4: "4ª", 5: "5ª", 6: "6ª (mais grave)"}


def open_note_of_string(tuning: list[str], string: int) -> str:
    """string=1 (mais aguda) → tuning[5]; string=6 → tuning[0]."""
    return list(reversed(tuning))[string - 1]


def capture_one_sample(stream_buffer: list, target_midi: int, target_freq: float) -> tuple[np.ndarray, float, float] | None:
    """Grava CAPTURE_SECONDS de áudio direto, pega a janela mais alta e roda YIN.

    Abordagem robusta: não espera trigger — só limpa o buffer, grava a janela
    inteira enquanto você toca, e depois analisa o trecho mais forte. Evita o bug
    de capturar o silêncio anterior à nota."""
    print(f"   🔴 GRAVANDO {CAPTURE_SECONDS:.1f}s — toque AGORA... ", end="", flush=True)

    stream_buffer.clear()
    time.sleep(CAPTURE_SECONDS)
    chunks = list(stream_buffer)  # snapshot (callback continua enchendo, mas isso basta)

    if not chunks:
        print("❌ sem áudio — device errado? (rode list_devices.py)")
        return None

    audio = np.concatenate(chunks)
    if len(audio) < BUFFER_SIZE:
        print("❌ áudio curto demais")
        return None

    # Janela de BUFFER_SIZE com mais energia (pega o ataque/sustain, ignora silêncio)
    best_rms = 0.0
    best_window = audio[:BUFFER_SIZE]
    for offset in range(0, len(audio) - BUFFER_SIZE, BUFFER_SIZE // 4):
        win = audio[offset : offset + BUFFER_SIZE]
        rms = float(np.sqrt(np.mean(win * win)))
        if rms > best_rms:
            best_rms = rms
            best_window = win

    if best_rms < 1e-5:
        print(f"❌ silêncio (pico {best_rms:.5f}) — aumente --gain ou o volume USB no M-EFCS")
        return None

    freq = yin(best_window, SAMPLE_RATE)
    if freq <= 0:
        print(f"❌ sem pitch claro (pico rms {best_rms:.4f}) — toque mais firme")
        return None

    # Validação: a freq detectada deve estar perto do esperado (±150 cents)
    detected_midi = freq_to_midi(freq)
    cents_off = (detected_midi - target_midi) * 100
    if abs(cents_off) > 150:
        print(f"⚠️  detectei {midi_to_note(int(round(detected_midi)))} @ {freq:.1f}Hz "
              f"({cents_off:+.0f}¢ do esperado {midi_to_note(target_midi)} @ {target_freq:.1f}Hz)")
        ans = input("      Aceitar mesmo assim? [s/N] ").strip().lower()
        if ans != "s":
            return None

    feats = extract_features(best_window, SAMPLE_RATE, freq)
    print(f"✓ {midi_to_note(int(round(detected_midi)))} @ {freq:.1f}Hz "
          f"({cents_off:+.0f}¢)  rms={best_rms:.4f}")
    return feats, freq, best_rms


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, help="ID do dispositivo de entrada")
    parser.add_argument("--gain", type=float, default=1.0, help="Multiplicador de ganho (use 5–20 se sinal fraco)")
    parser.add_argument("--tuning", default="standard", choices=list(TUNINGS.keys()))
    parser.add_argument("--frets", default=",".join(str(f) for f in DEFAULT_FRETS),
                        help=f"casas a amostrar, ex: '0,5,7,12,17' (default {','.join(str(f) for f in DEFAULT_FRETS)})")
    parser.add_argument("--samples", type=int, default=2, help="amostras por posição (default 2)")
    parser.add_argument("--resume", action="store_true", help="retoma calibração existente sem apagar")
    parser.add_argument("--output", default=str(SCRIPT_DIR / "calibration.json"),
                        help="caminho de saída (default: calibration.json na pasta do script)")
    args = parser.parse_args()

    frets = [int(x.strip()) for x in args.frets.split(",")]
    tuning = TUNINGS[args.tuning]

    if args.device is None:
        device = find_tank_g_device()
        if device is None:
            print("⚠️  TANK-G não encontrado. Especifique --device manualmente.")
            sys.exit(1)
    else:
        device = args.device

    output = Path(args.output)
    clf = FretClassifier()
    clf.tuning_name = args.tuning
    if args.resume and output.exists():
        clf.load(output)
        print(f"📂 Retomando calibração ({clf.n_calibrated_positions()} posições já gravadas)")

    info = sd.query_devices(device)
    print(f"\n🎸 Calibração TANK-G — Fret Detector v2")
    print(f"🎧 Dispositivo:  [{device}] {info['name']}")
    print(f"🎵 Afinação:     {args.tuning} ({' '.join(tuning)})")
    print(f"🎯 Casas:        {frets}")
    print(f"🔁 Amostras/pos: {args.samples}")
    print(f"💡 Dica: desligue distorção (BYPASS no M-EFCS) e palhete limpo.\n")

    # Buffer compartilhado entre callback e captura
    stream_buffer: list[np.ndarray] = []

    def callback(indata, frames, time_info, status):
        if status:
            pass  # silencia overflows comuns; o que importa é o áudio
        mono = indata[:, 0] * args.gain
        stream_buffer.append(mono.copy())
        # Limita acumulação (mantém ~3s de histórico)
        max_chunks = int(3.0 * SAMPLE_RATE / len(mono)) if len(mono) > 0 else 100
        if len(stream_buffer) > max_chunks:
            del stream_buffer[: len(stream_buffer) - max_chunks]

    positions = [(s, f) for s in range(1, 7) for f in frets]
    total = len(positions) * args.samples
    done_count = 0

    try:
        with sd.InputStream(
            device=device, samplerate=SAMPLE_RATE, channels=1,
            blocksize=1024, callback=callback,
        ):
            for string in range(1, 7):
                open_note = open_note_of_string(tuning, string)
                open_midi = note_to_midi(open_note)
                for fret in frets:
                    target_midi = open_midi + fret
                    target_freq = 440.0 * (2 ** ((target_midi - 69) / 12))

                    existing = len(clf.samples.get((string, fret), []))
                    if args.resume and existing >= args.samples:
                        done_count += args.samples
                        print(f"⏭️  {STRING_NAMES[string]} casa {fret} já tem {existing} amostras — pulando")
                        continue

                    target_note = midi_to_note(target_midi)
                    fret_label = "solta" if fret == 0 else f"casa {fret}"
                    print(f"\n{'=' * 60}")
                    print(f"[{done_count + 1}/{total}] Corda {STRING_NAMES[string]} — {fret_label}")
                    print(f"   Nota esperada: {target_note} ({target_freq:.1f}Hz)")
                    print(f"   Aperte ENTER quando pronto (ou 's' pra pular esta posição)")
                    cmd = input("   > ").strip().lower()
                    if cmd == "s":
                        print("   ⏭️  pulando")
                        done_count += args.samples
                        continue
                    if cmd == "q":
                        print("\n👋 saindo (vou salvar o que já tem)")
                        break

                    # Drena buffer antes de capturar (descarta ruído de "preparação")
                    stream_buffer.clear()

                    captured = 0
                    while captured < args.samples - existing:
                        result = capture_one_sample(stream_buffer, target_midi, target_freq)
                        if result is None:
                            ans = input("   Tentar de novo? [S/n] ").strip().lower()
                            if ans == "n":
                                break
                            stream_buffer.clear()
                            continue
                        feats, freq, rms = result
                        clf.add_calibration_sample(string, fret, feats)
                        captured += 1
                        done_count += 1
                        # pausa pra usuário soltar a corda
                        time.sleep(0.3)
                        stream_buffer.clear()

                else:
                    continue
                break  # se quebrou o for de fret, quebra o de string também

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo Ctrl+C — salvando o que tem")
    finally:
        clf.save_calibration(output)
        print(f"\n💾 Salvo em {output}")
        print(f"   Posições calibradas: {clf.n_calibrated_positions()} de {6 * len(frets)}")
        detector = SCRIPT_DIR / "fret_detector.py"
        print(f"\nAgora rode (pode ser de qualquer pasta):")
        print(f'   python "{detector}" --device {device} --gain {args.gain} --tuning {args.tuning} --classify')


if __name__ == "__main__":
    main()
