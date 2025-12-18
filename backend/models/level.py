"""
Backend Level Model: Level tile bilgilerini saklar
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TileType(Enum):
    """Tile tipleri - client ile aynı"""
    EMPTY = 0
    UNBREAKABLE = 1
    BREAKABLE = 2
    HARD = 3
    EXIT = 4


@dataclass(frozen=True)
class Tile:
    """Tile verisi"""
    x: int
    y: int
    type: TileType


@dataclass
class LevelData:
    """Level verisi - backend'de saklanır"""
    level_id: str
    width: int
    height: int
    tiles: dict[tuple[int, int], TileType]  # (x, y) -> TileType mapping
    
    def tile_at(self, x: int, y: int) -> TileType:
        """Belirtilen pozisyondaki tile tipini döndür"""
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return TileType.UNBREAKABLE  # Sınırlar dışı = duvar
        return self.tiles.get((x, y), TileType.EMPTY)
    
    def can_move_to(self, x: int, y: int) -> bool:
        """Bu pozisyona hareket edilebilir mi?"""
        tile_type = self.tile_at(x, y)
        # Sadece EMPTY ve EXIT tile'lara hareket edilebilir
        return tile_type in (TileType.EMPTY, TileType.EXIT)

