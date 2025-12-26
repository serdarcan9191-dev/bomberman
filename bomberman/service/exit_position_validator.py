"""
Exit Position Validator: Çıkış kapısı pozisyonunu doğrular ve düzeltir.
SOLID - Single Responsibility: Sadece exit position validasyonundan sorumlu.
"""
from __future__ import annotations

from typing import Tuple

from model.tile import Tile, TileType


class ExitPositionValidator:
    """Çıkış kapısı pozisyonunu doğrular ve gerekirse düzeltir."""

    @staticmethod
    def validate_and_fix(
        exit_position: Tuple[int, int],
        tile_map: dict[Tuple[int, int], Tile],
        width: int,
        height: int,
    ) -> Tuple[int, int]:
        """
        Exit position'ı doğrular. Eğer geçersizse (UNBREAKABLE/HARD üzerindeyse),
        en yakın geçerli pozisyona taşır.
        
        Returns:
            Geçerli exit position (x, y)
        """
        x, y = exit_position
        
        # Sınır kontrolü
        if not (0 <= x < width and 0 <= y < height):
            # Sınır dışındaysa, merkeze yakın bir pozisyon bul
            return ExitPositionValidator._find_nearest_valid_position(
                (width // 2, height // 2), tile_map, width, height
            )
        
        # Mevcut pozisyonu kontrol et
        current_tile = tile_map.get((x, y))
        if current_tile is None:
            # Tile yoksa, en yakın geçerli pozisyonu bul
            return ExitPositionValidator._find_nearest_valid_position(
                exit_position, tile_map, width, height
            )
        
        # Eğer pozisyon geçerliyse (EMPTY veya BREAKABLE), olduğu gibi döndür
        if current_tile.type in (TileType.EMPTY, TileType.BREAKABLE):
            return exit_position
        
        # UNBREAKABLE veya HARD üzerindeyse, en yakın geçerli pozisyonu bul
        return ExitPositionValidator._find_nearest_valid_position(
            exit_position, tile_map, width, height
        )
    
    @staticmethod
    def _find_nearest_valid_position(
        start: Tuple[int, int],
        tile_map: dict[Tuple[int, int], Tile],
        width: int,
        height: int,
    ) -> Tuple[int, int]:
        """Başlangıç pozisyonundan en yakın geçerli pozisyonu bulur (BFS)"""
        from collections import deque
        
        start_x, start_y = start
        visited = set()
        queue = deque([(start_x, start_y, 0)])  # (x, y, distance)
        
        # BFS ile en yakın geçerli pozisyonu bul
        while queue:
            x, y, distance = queue.popleft()
            
            # Sınır kontrolü
            if not (0 <= x < width and 0 <= y < height):
                continue
            
            pos = (x, y)
            if pos in visited:
                continue
            visited.add(pos)
            
            tile = tile_map.get(pos)
            if tile is None:
                continue
            
            # Geçerli pozisyon mu? (EMPTY veya BREAKABLE)
            if tile.type in (TileType.EMPTY, TileType.BREAKABLE):
                return pos
            
            # Komşuları ekle
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                queue.append((x + dx, y + dy, distance + 1))
        
        # Hiç geçerli pozisyon bulunamazsa, varsayılan pozisyon döndür
        # (Genellikle oyuncu başlangıç pozisyonu yakını)
        return (1, 1)

