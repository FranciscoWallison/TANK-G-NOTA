"""Gera imagens-ilustração da interface do afinador (tuner.py) para o README.

Não é um screenshot de captura — é uma renderização fiel do layout do tuner.py
feita com Pillow, pra documentação. Roda:  python docs/generate_mockup.py
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 720, 480
BG = (30, 30, 30)
FG = (240, 240, 240)
DIM = (119, 119, 119)
GREEN = (76, 175, 80)
YELLOW = (255, 193, 7)
RED = (244, 67, 54)
TRACK = (43, 43, 43)

CENTS_RANGE = 50
CENTS_GREEN = 5
CENTS_YELLOW = 15


def load_font(names, size):
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


MONO_BIG = load_font(["consolab.ttf", "consola.ttf", "DejaVuSansMono-Bold.ttf"], 130)
MONO_MID = load_font(["consola.ttf", "DejaVuSansMono.ttf"], 20)
MONO_SM = load_font(["consola.ttf", "DejaVuSansMono.ttf"], 13)
SANS = load_font(["arial.ttf", "DejaVuSans.ttf"], 15)
SANS_BOLD = load_font(["arialbd.ttf", "DejaVuSans-Bold.ttf"], 17)


def color_for_cents(c):
    a = abs(c)
    if a <= CENTS_GREEN:
        return GREEN
    if a <= CENTS_YELLOW:
        return YELLOW
    return RED


def centered(draw, cx, y, text, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    w = bb[2] - bb[0]
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def draw_cents_bar(draw, cy, cents):
    margin = 80
    x0, x1 = margin, W - margin
    mid = (x0 + x1) // 2
    half = (x1 - x0) // 2
    h = 12

    def cents_to_x(c):
        c = max(-CENTS_RANGE, min(CENTS_RANGE, c))
        return mid + int((c / CENTS_RANGE) * half)

    # trilha de fundo
    draw.rectangle([x0, cy - h // 2, x1, cy + h // 2], fill=TRACK)
    gh = int((CENTS_GREEN / CENTS_RANGE) * half)
    yh = int((CENTS_YELLOW / CENTS_RANGE) * half)
    # vermelho (extremos)
    draw.rectangle([x0, cy - h // 2, mid - yh, cy + h // 2], fill=RED)
    draw.rectangle([mid + yh, cy - h // 2, x1, cy + h // 2], fill=RED)
    # amarelo
    draw.rectangle([mid - yh, cy - h // 2, mid - gh, cy + h // 2], fill=YELLOW)
    draw.rectangle([mid + gh, cy - h // 2, mid + yh, cy + h // 2], fill=YELLOW)
    # verde (centro)
    draw.rectangle([mid - gh, cy - h // 2, mid + gh, cy + h // 2], fill=GREEN)

    # ticks
    for c in (-50, -25, -15, -5, 0, 5, 15, 25, 50):
        x = cents_to_x(c)
        th = 10 if c in (-50, 0, 50) else 6
        draw.line([x, cy + h // 2 + 4, x, cy + h // 2 + 4 + th], fill=DIM)
        if c in (-50, -25, 0, 25, 50):
            centered(draw, x, cy + h // 2 + 18, f"{c:+d}", MONO_SM, DIM)

    # agulha
    nx = cents_to_x(cents)
    col = color_for_cents(cents)
    draw.polygon([(nx - 9, cy - 26), (nx + 9, cy - 26), (nx, cy - 8)], fill=col)
    draw.rectangle([nx - 2, cy - 8, nx + 2, cy + 8], fill=col)


def render(note, freq, cents, target_label, status_text, status_color,
           action_text, tuning="auto (cromático)", filename="tuner.png"):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    col = color_for_cents(cents)

    # topo
    d.text((16, 14), "Afinacao alvo:", font=SANS, fill=DIM)
    d.text((140, 12), f" {tuning} ", font=SANS, fill=FG)
    bb = d.textbbox((0, 0), status_text, font=SANS)
    d.text((W - 16 - (bb[2] - bb[0]), 14), status_text, font=SANS, fill=status_color)

    # nota gigante
    centered(d, W // 2, 70, note, MONO_BIG, col)
    # freq
    centered(d, W // 2, 230, f"{freq:.2f} Hz", MONO_MID, FG)
    # alvo
    centered(d, W // 2, 262, target_label, SANS, DIM)
    # barra
    draw_cents_bar(d, 330, cents)
    # ação
    centered(d, W // 2, 388, action_text, SANS_BOLD, col)
    # cents numérico
    centered(d, W // 2, 416, f"{cents:+.1f} cents", MONO_SM, col)

    out = OUT_DIR / filename
    img.save(out)
    print(f"gerado: {out}")


if __name__ == "__main__":
    # Cena 1: afinado (verde)
    render(
        note="E2", freq=82.41, cents=0.0,
        target_label="alvo: E2 (82.41 Hz) - standard",
        status_text="ouvindo", status_color=GREEN,
        action_text="AFINADO", tuning="standard", filename="tuner_afinado.png",
    )
    # Cena 2: precisa descer (amarelo)
    render(
        note="A2", freq=111.3, cents=20.0,
        target_label="alvo: A2 (110.00 Hz) - standard",
        status_text="ouvindo", status_color=GREEN,
        action_text="descer (20 cents)", tuning="standard", filename="tuner_descer.png",
    )
