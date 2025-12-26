"""
Pygame tabanlı View katmanı: görüntüleme döngüsü ve temel render işlemleri.
Bu sınıf diğer katmanlardan bağımsız kalmalı; sadece kendisine gönderilen çizim komutlarını işler.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from .scene_manager import SceneManager


ConfigColor = Tuple[int, int, int]


@dataclass(frozen=True)
class ViewConfig:
    """Pygame ekranı için temel yapılandırma."""

    width: int = 1280
    height: int = 720
    fps: int = 60
    background_color: ConfigColor = (0, 0, 0)
    grid_color: ConfigColor = (32, 32, 48)


class PygameView:
    """Pygame uygulamasını yöneten basit bir renderer."""

    def __init__(self, config: ViewConfig) -> None:
        self._config = config
        self._screen: Optional[pygame.Surface] = None
        self._clock: Optional[pygame.time.Clock] = None
        self._fullscreen = False
        self._windowed_size = (config.width, config.height)

    def initialize(self) -> None:
        """Pygame'i başlatır ve ekranı hazırlar."""
        pygame.init()
        self._screen = pygame.display.set_mode((self._config.width, self._config.height))
        pygame.display.set_caption("Bomberman - View Katmanı")
        self._clock = pygame.time.Clock()

    def shutdown(self) -> None:
        """Pygame kaynaklarını temizler."""
        pygame.quit()

    def _draw_grid(self) -> None:
        """Basit bir ızgara çizimi, boş alanların düzenini göstermek için."""
        cell_size = 40
        width, height = self._screen.get_size()

        for x in range(0, width, cell_size):
            pygame.draw.line(self._screen, self._config.grid_color, (x, 0), (x, height), 1)
        for y in range(0, height, cell_size):
            pygame.draw.line(self._screen, self._config.grid_color, (0, y), (width, y), 1)

    def _poll_events(self) -> list[pygame.event.Event]:
        """Pygame olay kuyruğunu toplar."""
        return list(pygame.event.get())

    def render(self, scene_manager: SceneManager, run_seconds: Optional[float] = None) -> None:
        """
        View döngüsünü çalıştırır ve verilen sahneyi yönetir.

        :param scene_manager: Hangi sahnenin çizileceğini yöneten yönetici.
        :param run_seconds: İsteğe bağlı max süre (test/kontrol amacıyla).
        """
        if self._screen is None or self._clock is None:
            raise RuntimeError("View initialize() çağrılmadan render edilemez.")

        running = True
        elapsed = 0.0
        while running:
            delta = self._clock.tick(self._config.fps) / 1000.0
            elapsed += delta

            events = self._poll_events()
            if any(event.type == pygame.QUIT for event in events):
                running = False

            scene = scene_manager.current
            scene.handle_events(events)
            scene.update(delta)

            self._screen.fill(self._config.background_color)
            self._draw_grid()
            scene.draw(self._screen)
            pygame.display.flip()

            if run_seconds and elapsed >= run_seconds:
                running = False

    def toggle_fullscreen(self) -> None:
        """Pencereyi fullscreen mod ve normal mod arasında değiştirir."""
        if self._screen is None:
            return

        self._fullscreen = not self._fullscreen

        if self._fullscreen:
            self._windowed_size = self._screen.get_size()
            info = pygame.display.Info()
            size = (info.current_w, info.current_h)
            flags = pygame.FULLSCREEN
        else:
            size = self._windowed_size
            flags = 0

        self._screen = pygame.display.set_mode(size, flags)

