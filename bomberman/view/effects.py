"""
Patlamalar / bomba efektleri için asset tanımlamaları.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pygame

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def load_effect_image(name: str) -> pygame.Surface | None:
    path = ASSETS_DIR / name
    if not path.exists():
        return None
    return pygame.image.load(path).convert_alpha()


def load_effect_sound(name: str) -> pygame.mixer.Sound | None:
    path = ASSETS_DIR / name
    if not path.exists():
        return None
    return pygame.mixer.Sound(path)


@dataclass(frozen=True)
class Effect:
    id: str
    name: str
    image_name: str
    description: str


class EffectFactory:
    @staticmethod
    def roster() -> Sequence[Effect]:
        return [
            Effect(id="bomb", name="Bomb", image_name="bomb.png", description="Countdown / patlayıcı."),
            Effect(id="explosion", name="Explosion", image_name="Explosion.png", description="Patlama görseli."),
        ]

