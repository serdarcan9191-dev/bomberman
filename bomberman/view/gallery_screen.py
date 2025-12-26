"""
Karakter ve canavar görsellerini sergileyen sahne.
"""
from __future__ import annotations

from typing import Iterable

import pygame

from .characters import CharacterFactory, MonsterFactory, load_asset_image
from .effects import EffectFactory, load_effect_image
from .main_menu import MenuTheme
from .scene import Scene
from .scene_manager import SceneManager
from .terminal_theme import get_terminal_font, draw_terminal_text, draw_terminal_box


class GalleryScreen(Scene):
    def __init__(self, manager: "SceneManager", theme: "MenuTheme") -> None:
        self._theme = theme
        self._manager = manager
        self._font = get_terminal_font(16)
        self._heading = get_terminal_font(32)
        self._items = list(CharacterFactory.roster()) + list(MonsterFactory.roster()) + list(EffectFactory.roster())

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self._manager.return_to_menu(show_loading=True)

    def update(self, delta: float) -> None:
        del delta

    def draw(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        surface.fill(self._theme.background)

        # Terminal stili başlık
        draw_terminal_text(surface, "KARAKTER & DUSMANLAR", self._heading, self._theme.title, (width // 2, 40), "center")

        margin = 30
        item_width = min(140, (width - margin * 2) // len(self._items))
        item_height = 200
        start_x = (width - (item_width + margin) * len(self._items) + margin) // 2
        y = 100

        cols = max(1, (width - margin * 2) // (item_width + margin))
        cols = min(cols, len(self._items))
        rows = (len(self._items) + cols - 1) // cols
        total_width = cols * item_width + (cols - 1) * margin
        total_height = rows * item_height + (rows - 1) * margin
        start_x = (width - total_width) // 2

        for idx, item in enumerate(self._items):
            col = idx % cols
            row = idx // cols
            rect = pygame.Rect(
                start_x + col * (item_width + margin),
                y + row * (item_height + margin),
                item_width,
                item_height,
            )
            # Terminal stili kutu
            draw_terminal_box(surface, rect, self._theme.panel_accent, self._theme.panel, 1)
            
            picker = load_asset_image if hasattr(item, "image_name") else load_effect_image
            image = picker(item.image_name) if item.image_name else None
            if image:
                scaled = pygame.transform.smoothscale(image, (int(rect.width * 0.6), int(rect.height * 0.4)))
                img_rect = scaled.get_rect(center=(rect.centerx, rect.top + rect.height * 0.35))
                surface.blit(scaled, img_rect)

            # Terminal stili isim
            draw_terminal_text(surface, item.name, self._font, self._theme.text, (rect.centerx, rect.bottom - 30), "center")

        draw_terminal_text(surface, "ESC: Menuye don", self._font, self._theme.text, (width // 2, height - 30), "center")

