"""
Terminal Theme Helper: Terminal görünümü için yardımcı fonksiyonlar
"""
from __future__ import annotations

import pygame


def get_terminal_font(size: int) -> pygame.font.Font:
    """
    Terminal için monospace font döndür.
    Windows'ta Consolas, yoksa Courier New, yoksa default monospace.
    """
    try:
        # Windows'ta Consolas
        font = pygame.font.SysFont("consolas", size)
        # Font'un yüklenip yüklenmediğini kontrol et
        test_surf = font.render("Test", True, (255, 255, 255))
        if test_surf.get_width() == 0:
            raise ValueError("Consolas not available")
        return font
    except:
        try:
            # Courier New
            font = pygame.font.SysFont("courier new", size)
            test_surf = font.render("Test", True, (255, 255, 255))
            if test_surf.get_width() == 0:
                raise ValueError("Courier New not available")
            return font
        except:
            # Fallback: default monospace
            return pygame.font.Font(None, size)


def draw_terminal_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    pos: tuple[int, int],
    align: str = "left"
) -> pygame.Rect:
    """
    Terminal stilinde metin çiz.
    
    Args:
        surface: Pygame surface
        text: Çizilecek metin
        font: Font
        color: Renk (RGB)
        pos: Pozisyon (x, y)
        align: "left", "center", "right"
    
    Returns:
        Text rect
    """
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect()
    
    if align == "center":
        text_rect.center = pos
    elif align == "right":
        text_rect.right = pos[0]
        text_rect.top = pos[1]
    else:  # left
        text_rect.left = pos[0]
        text_rect.top = pos[1]
    
    surface.blit(text_surf, text_rect)
    return text_rect


def draw_terminal_box(
    surface: pygame.Surface,
    rect: pygame.Rect,
    border_color: tuple[int, int, int] = (255, 255, 255),
    fill_color: tuple[int, int, int] | None = None,
    border_width: int = 1
) -> None:
    """
    Terminal stilinde kutu çiz (basit, köşeler yuvarlatılmamış).
    
    Args:
        surface: Pygame surface
        rect: Kutu rect
        border_color: Kenarlık rengi
        fill_color: Dolgu rengi (None ise doldurulmaz)
        border_width: Kenarlık kalınlığı
    """
    if fill_color:
        pygame.draw.rect(surface, fill_color, rect)
    pygame.draw.rect(surface, border_color, rect, width=border_width)

