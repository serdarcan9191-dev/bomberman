"""
Tile tanımları ve tipleri.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TileType(Enum):
    EMPTY = 0
    UNBREAKABLE = 1
    BREAKABLE = 2
    HARD = 3
    EXIT = 4


@dataclass(frozen=True)
class Tile:
    x: int
    y: int
    type: TileType

