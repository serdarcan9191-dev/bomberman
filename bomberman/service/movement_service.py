"""
Movement Service: Düşman hareket kontrollerini yöneten servis.
SOLID - Single Responsibility: Sadece hareket kontrollerinden sorumlu.

4 Yönlü Hareket:
- Kuzey (North): (0, -1)
- Güney (South): (0, 1)
- Doğu (East): (1, 0)
- Batı (West): (-1, 0)
"""
from __future__ import annotations

from typing import Callable

from model.level import TileType


class MovementService:
    """Düşman hareket kontrollerini yöneten servis - sadece 4 yönlü hareket"""

    @staticmethod
    def can_move_to(
        x: int,
        y: int,
        tile_provider: Callable[[int, int], TileType],
    ) -> bool:
        """
        Belirtilen pozisyona hareket edilebilir mi?
        Sadece EMPTY ve EXIT tile'larına hareket edilebilir.
        """
        tile_type = tile_provider(x, y)
        return tile_type in (TileType.EMPTY, TileType.EXIT)

