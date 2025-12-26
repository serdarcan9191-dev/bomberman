"""
View katmanındaki sahneleri tanımlayan tip protokolleri.
"""
from __future__ import annotations

from typing import Iterable, Protocol

import pygame


class Scene(Protocol):
    """Bir sahne update/draw döngüsüne katılabilir."""

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        ...

    def update(self, delta: float) -> None:
        ...

    def draw(self, surface: pygame.Surface) -> None:
        ...

