"""
Lobi ekranı: aktif odaları listeler ve menüye dönme seçeneği sunar.
"""
from __future__ import annotations

from typing import Iterable

import pygame

from .main_menu import MenuTheme
from .scene import Scene
from .scene_manager import SceneManager
from .terminal_theme import get_terminal_font, draw_terminal_text, draw_terminal_box


class LobbyRoom:
    def __init__(self, name: str, players: str, status: str) -> None:
        self.name = name
        self.players = players
        self.status = status


class LobbyScreen(Scene):
    def __init__(self, manager: SceneManager, theme: MenuTheme | None = None) -> None:
        self._manager = manager
        self._theme = theme or MenuTheme.default()
        # Server'dan gelecek gerçek lobiler (şu an boş)
        self._rooms = []
        self._selected = 0
        pygame.font.init()
        self._title_font = get_terminal_font(40)
        self._item_font = get_terminal_font(18)
        self._hint_font = get_terminal_font(14)
        self._info_font = get_terminal_font(20)

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._manager.return_to_menu(show_loading=True)
                elif len(self._rooms) > 0:
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        self._selected = (self._selected + 1) % len(self._rooms)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self._selected = (self._selected - 1) % len(self._rooms)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        print(f"Lobi seçeneği: {self._rooms[self._selected].name}")

    def update(self, delta: float) -> None:
        del delta

    def draw(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        surface.fill(self._theme.background)

        # Terminal stili başlık
        draw_terminal_text(surface, "HAZIR LOBILER", self._title_font, self._theme.title, (width // 2, 60), "center")

        list_rect = pygame.Rect(60, 110, width - 120, height - 220)
        draw_terminal_box(surface, list_rect, self._theme.panel_accent, self._theme.panel, 2)

        # Eğer oda yoksa bilgilendirme mesajı göster
        if not self._rooms:
            draw_terminal_text(surface, "Su an aktif lobi yok", self._info_font, self._theme.text, (width // 2, height // 2 - 50), "center")
            draw_terminal_text(surface, "Multiplayer icin 'Cok Oyunculu' secenegini kullanin", self._item_font, self._theme.panel_accent, (width // 2, height // 2 + 10), "center")
        else:
            # Lobiler varsa listele - terminal stili
            item_height = 50
            gap = 10
            for idx, room in enumerate(self._rooms):
                rect = pygame.Rect(
                    list_rect.x + 20,
                    list_rect.y + 20 + idx * (item_height + gap),
                    list_rect.width - 40,
                    item_height,
                )
                border_color = self._theme.accent if idx == self._selected else self._theme.panel_accent
                fill_color = self._theme.panel if idx == self._selected else self._theme.background
                draw_terminal_box(surface, rect, border_color, fill_color, 1)

                # Text
                room_text = f"{room.name} | {room.players} | {room.status}"
                text_color = self._theme.title if idx == self._selected else self._theme.text
                draw_terminal_text(surface, room_text, self._item_font, text_color, (rect.left + 10, rect.centery), "left")
        
        draw_terminal_text(surface, "ESC: Menuye don  |  ENTER: Katil", self._hint_font, self._theme.text, (width // 2, height - 30), "center")

