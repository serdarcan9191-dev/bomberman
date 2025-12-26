"""
Yeni oyun başlangıç ekranı: oyun kurgusunu gösteren sahne.
"""
from __future__ import annotations

from typing import Iterable

import pygame

from .main_menu import MenuTheme
from .pygame_view import ViewConfig
from .scene import Scene
from .scene_manager import SceneManager
from .terminal_theme import get_terminal_font, draw_terminal_text, draw_terminal_box


class NewGameScreen(Scene):
    def __init__(
        self,
        manager: SceneManager,
        config: ViewConfig,
        theme: MenuTheme | None = None,
    ) -> None:
        self._manager = manager
        self._config = config
        self._theme = theme or MenuTheme.default()
        self._title_font = get_terminal_font(40)
        self._body_font = get_terminal_font(18)
        self._hint_font = get_terminal_font(14)
        self._grid_cols = 13
        self._grid_rows = 11

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._manager.return_to_menu(show_loading=True)

    def update(self, delta: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        surface.fill(self._theme.background)
        
        # Terminal stili başlık
        draw_terminal_text(surface, "YENI OYUN HAZIRLANIYOR", self._title_font, self._theme.title, (width // 2, 70), "center")

        body = [
            "Bombalari yerlestirme alani gorunumdur.",
            "Oyunculara ozel yetenekler sirayla secilecek.",
            "ESC: Menuye don."
        ]

        for idx, line in enumerate(body):
            draw_terminal_text(surface, line, self._body_font, self._theme.text, (width // 2, 130 + idx * 25), "center")

        draw_terminal_text(surface, "ESC: Menuye don", self._hint_font, self._theme.text, (width // 2, height - 30), "center")

    def _draw_board(self, surface: pygame.Surface, width: int, height: int) -> None:
        """Terminal stili board - basit grid"""
        board_size = min(width, height) * 0.4
        square_size = board_size / max(self._grid_cols, self._grid_rows)
        offset_x = (width - board_size) / 2
        offset_y = (height - board_size) / 2 + 60

        for row in range(self._grid_rows):
            for col in range(self._grid_cols):
                rect = pygame.Rect(
                    offset_x + col * square_size,
                    offset_y + row * square_size,
                    square_size - 1,
                    square_size - 1,
                )
                color = self._theme.panel if (row + col) % 2 == 0 else self._theme.panel_accent
                draw_terminal_box(surface, rect, self._theme.panel_accent, color, 1)

