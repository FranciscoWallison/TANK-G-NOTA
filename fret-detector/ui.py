"""Helpers de UI em Pygame compartilhados pelas telas do TANK-G Studio."""
import pygame

# Paleta (consistente com tuner/game)
BG = (18, 18, 22)
PANEL = (30, 30, 38)
PANEL_HI = (44, 44, 56)
FG = (240, 240, 240)
DIM = (130, 130, 145)
GREEN = (76, 200, 120)
YELLOW = (255, 193, 7)
RED = (244, 67, 54)
ACCENT = (90, 160, 255)

# cores por corda (corda 6→1 = índice 0→5), igual ao jogo
LANE_COLORS = [
    (231, 76, 60), (230, 126, 34), (241, 196, 15),
    (46, 204, 113), (52, 152, 219), (155, 89, 182),
]


def font(size, bold=False):
    for name in ("Consolas", "DejaVu Sans Mono", "Courier New"):
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            continue
    return pygame.font.Font(None, size)


def draw_text(surf, text, fnt, color, center=None, topleft=None, midtop=None):
    img = fnt.render(text, True, color)
    rect = img.get_rect()
    if center is not None:
        rect.center = center
    elif midtop is not None:
        rect.midtop = midtop
    else:
        rect.topleft = topleft or (0, 0)
    surf.blit(img, rect)
    return rect


def draw_beat_pulse(surf, cx, cy, intensity, is_accent, base_radius=18):
    """Círculo que pulsa com a batida do metrônomo. intensity 0..1 (decai)."""
    intensity = max(0.0, min(1.0, intensity))
    col = YELLOW if is_accent else GREEN
    rgb = tuple(int(c * intensity) for c in col)
    r = int(base_radius * (1.4 if is_accent else 1.0) * (0.55 + 0.45 * intensity))
    if r > 0:
        pygame.draw.circle(surf, rgb, (int(cx), int(cy)), r)
    pygame.draw.circle(surf, col, (int(cx), int(cy)), max(r, 4), 2)


def level_bar(surf, rect, rms, peak=0.3):
    """Barra de nível de sinal (0..peak). rect = (x, y, w, h)."""
    x, y, w, h = rect
    pygame.draw.rect(surf, PANEL, (x, y, w, h), border_radius=4)
    frac = max(0.0, min(1.0, rms / peak))
    fill_w = int(w * frac)
    col = GREEN if frac > 0.06 else DIM
    if fill_w > 0:
        pygame.draw.rect(surf, col, (x, y, fill_w, h), border_radius=4)


class Button:
    def __init__(self, rect, label, on_click, fnt=None, color=PANEL,
                 hover=PANEL_HI, text_color=FG):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.fnt = fnt
        self.color = color
        self.hover = hover
        self.text_color = text_color
        self._hovered = False

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos) and self.on_click:
                self.on_click()
                return True
        return False

    def draw(self, surf):
        col = self.hover if self._hovered else self.color
        pygame.draw.rect(surf, col, self.rect, border_radius=10)
        pygame.draw.rect(surf, PANEL_HI, self.rect, width=1, border_radius=10)
        fnt = self.fnt or font(22, bold=True)
        draw_text(surf, self.label, fnt, self.text_color, center=self.rect.center)
