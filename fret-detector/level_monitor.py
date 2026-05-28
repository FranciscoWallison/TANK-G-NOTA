"""Monitor de nível de áudio — debug para ver se o sinal está chegando.

Uso:
    python level_monitor.py             # auto-detecta USB-Audio
    python level_monitor.py --device 27 # testa um ID específico
"""
import argparse
import sys
import time
import numpy as np
import sounddevice as sd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def find_usb_device():
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and "usb-audio" in d["name"].lower():
            return i
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=int, default=None)
    args = parser.parse_args()

    device = args.device if args.device is not None else find_usb_device()
    if device is None:
        print("Nenhum USB-Audio encontrado.")
        return

    info = sd.query_devices(device)
    channels = int(info["max_input_channels"])
    print(f"📡 Monitorando: [{device}] {info['name']}")
    print(f"   Sample rate suportado: {info['default_samplerate']:.0f} Hz")
    print(f"   Canais de input: {channels}")
    print("   Toque na guitarra (Ctrl+C para sair)\n")

    peak_l_ever = 0.0
    peak_r_ever = 0.0

    def callback(indata, frames, time_info, status):
        nonlocal peak_l_ever, peak_r_ever
        if status:
            print(f"⚠️  status: {status}", file=sys.stderr)

        ch_l = indata[:, 0]
        rms_l = float(np.sqrt(np.mean(ch_l * ch_l)))
        peak_l = float(np.max(np.abs(ch_l)))
        peak_l_ever = max(peak_l_ever, peak_l)

        if indata.shape[1] > 1:
            ch_r = indata[:, 1]
            rms_r = float(np.sqrt(np.mean(ch_r * ch_r)))
            peak_r = float(np.max(np.abs(ch_r)))
            peak_r_ever = max(peak_r_ever, peak_r)
        else:
            rms_r = peak_r = 0.0

        bar_l = "█" * int(min(rms_l * 200, 30)) + "·" * (30 - int(min(rms_l * 200, 30)))
        bar_r = "█" * int(min(rms_r * 200, 30)) + "·" * (30 - int(min(rms_r * 200, 30)))
        marker = " 🔴" if max(rms_l, rms_r) > 0.001 else "  "
        print(
            f"\rL: {rms_l:.4f} |{bar_l}|  R: {rms_r:.4f} |{bar_r}|"
            f"  pico L:{peak_l_ever:.3f} R:{peak_r_ever:.3f}{marker}",
            end="", flush=True,
        )

    try:
        with sd.InputStream(device=device, samplerate=44100, channels=channels, blocksize=1024, callback=callback):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\n\n📊 Pico L: {peak_l_ever:.4f}   Pico R: {peak_r_ever:.4f}")
        if max(peak_l_ever, peak_r_ever) < 0.001:
            print("❌ Nenhum sinal em nenhum canal. Tente outro --device ou configure roteamento USB no M-EFCS.")
        elif max(peak_l_ever, peak_r_ever) < 0.01:
            print("⚠️  Sinal MUITO baixo. Aumente o MASTER do TANK-G e bata mais forte.")
        else:
            print("✅ Sinal OK!")
            if peak_l_ever > peak_r_ever * 3:
                print("   → Sinal está no canal ESQUERDO (canal 0). Detector já usa esse.")
            elif peak_r_ever > peak_l_ever * 3:
                print("   → Sinal está no canal DIREITO (canal 1). Preciso ajustar o detector!")
            else:
                print("   → Sinal em ambos os canais.")


if __name__ == "__main__":
    main()
