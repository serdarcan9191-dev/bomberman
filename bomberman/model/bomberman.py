from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from view.characters import Character


@dataclass
class Bomberman:
    character: Character
    position: Tuple[int, int]
    health: int = 80
    speed: float = 1.0
    powerups: set[str] = field(default_factory=set)
    bomb_count: int = 1  # Maksimum aynı anda koyabileceği bomba sayısı
    bomb_power: int = 1  # Bomba patlama yarıçapı

    def take_damage(self, amount: int = 1) -> None:
        self.health = max(0, self.health - amount)

    def heal(self, amount: int = 1) -> None:
        self.health += amount

    def is_alive(self) -> bool:
        return self.health > 0

    def apply_powerup(self, powerup: str) -> None:
        self.powerups.add(powerup)
        if powerup == "speed":
            self.speed *= 1.25
        elif powerup == "bomb_count":
            self.bomb_count += 1
        elif powerup == "bomb_power":
            self.bomb_power += 1

    def remove_powerup(self, powerup: str) -> None:
        self.powerups.discard(powerup)

