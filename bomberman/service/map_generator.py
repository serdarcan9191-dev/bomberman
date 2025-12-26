"""
Basit harita oluşturma servisi.
SOLID - Single Responsibility: Harita oluşturmaktan sorumlu.
"""
from __future__ import annotations

import hashlib
import random
from typing import Dict, Tuple

from model.tile import Tile, TileType
from service.exit_position_validator import ExitPositionValidator


class MapGenerator:
    """
    Basit ve net harita oluşturucu.
    Tüm mantık burada, karmaşık pipeline yok.
    """
    
    @staticmethod
    def generate_tiles(
        width: int,
        height: int,
        exit_position: Tuple[int, int],
        breakable_positions: tuple[Tuple[int, int], ...],
        hard_positions: tuple[Tuple[int, int], ...],
        extra_unbreakable: tuple[Tuple[int, int], ...],
    ) -> list[Tile]:
        """
        Basit harita oluşturma.
        
        Sıra:
        1. Sabit duvarlar (UNBREAKABLE)
        2. Ekstra sabit duvarlar
        3. Hard duvarlar (sadece EMPTY üzerine)
        4. Breakable duvarlar (sadece EMPTY üzerine)
        5. Exit doğrulama ve yerleştirme
        """
        # 1. Haritayı başlat
        tile_map: Dict[Tuple[int, int], Tile] = {}
        
        # Tüm haritayı EMPTY ile başlat
        for y in range(height):
            for x in range(width):
                tile_map[(x, y)] = Tile(x, y, TileType.EMPTY)
        
        # Sabit duvarlar: Üst ve alt satırlar
        for x in range(width):
            tile_map[(x, 0)] = Tile(x, 0, TileType.UNBREAKABLE)
            tile_map[(x, height - 1)] = Tile(x, height - 1, TileType.UNBREAKABLE)
        
        # Sabit duvarlar: Grid pattern (çift x ve çift y, 2'den başlayarak)
        for x in range(0, width, 2):
            for y in range(2, height - 1, 2):
                tile_map[(x, y)] = Tile(x, y, TileType.UNBREAKABLE)
        
        # 2. Ekstra sabit duvarlar
        for pos in extra_unbreakable:
            tile_map[pos] = Tile(pos[0], pos[1], TileType.UNBREAKABLE)
        
        # 3. Hard duvarlar (sadece EMPTY üzerine)
        for pos in hard_positions:
            if tile_map[pos].type == TileType.EMPTY:
                tile_map[pos] = Tile(pos[0], pos[1], TileType.HARD)
        
        # 4. Breakable duvarlar (sadece EMPTY üzerine)
        for pos in breakable_positions:
            if tile_map[pos].type == TileType.EMPTY:
                tile_map[pos] = Tile(pos[0], pos[1], TileType.BREAKABLE)
        
        # 5. Exit doğrulama ve yerleştirme
        validated_exit = ExitPositionValidator.validate_and_fix(
            exit_position, tile_map, width, height
        )
        tile_map[validated_exit] = Tile(validated_exit[0], validated_exit[1], TileType.EXIT)
        
        return list(tile_map.values())
    
    @staticmethod
    def generate_positions(
        level_id: str,
        width: int,
        height: int,
        enemy_count: int,
        level_number: int,
        player_start: Tuple[int, int],
    ) -> dict[str, list[Tuple[int, int]] | Tuple[int, int]]:
        """
        Basit pozisyon üretici - sadece rastgele yerleştirme.
        
        Kurallar:
        - Exit: Basit hesaplama (sağ alt köşeye yakın)
        - Level 2 için özel: Çok az düşman ve duvar
        - Breakable: Level 2 için 2, diğerleri için enemy_count
        - Hard: Level 2 için 0, diğerleri için level_number // 2 (maksimum 3)
        - Enemy: enemy_count kadar (oyuncudan minimum 3 uzaklık)
        """
        # Deterministik seed
        seed = MapGenerator._generate_seed(level_id)
        rng = random.Random(seed)
        
        # Kullanılabilir pozisyonlar
        available = MapGenerator._calculate_available_positions(width, height)
        
        # Oyuncu ve çevresini hariç tut
        player_x, player_y = player_start
        exclude = set()
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if abs(dx) + abs(dy) <= 2:
                    x, y = player_x + dx, player_y + dy
                    if 0 <= x < width and 0 <= y < height:
                        exclude.add((x, y))
        
        available = [pos for pos in available if pos not in exclude]
        rng.shuffle(available)
        
        positions: dict[str, list[Tuple[int, int]] | Tuple[int, int]] = {
            'enemy': [],
            'breakable': [],
            'hard': [],
            'extra_unbreakable': [],
            'exit': (width - 2, height - 2),  # Basit: sağ alt köşe
        }
        
        used = set()
        
        # 1. Düşmanları yerleştir
        for _ in range(enemy_count):
            if not available:
                break
            
            # Oyuncudan minimum 3 uzaklıkta olan pozisyon bul
            for i, pos in enumerate(available):
                if pos in used:
                    continue
                x, y = pos
                distance = abs(x - player_x) + abs(y - player_y)
                if distance >= 3:
                    positions['enemy'].append(pos)
                    used.add(pos)
                    available.pop(i)
                    break
        
        # 2. Hard duvarları yerleştir (önce)
        # Seviye 1-3: 0, Seviye 4-5: 1, Seviye 6-7: 2, Seviye 8+: 3 (maksimum)
        hard_count = max(0, min((level_number - 1) // 2, 3))
        
        for _ in range(min(hard_count, len(available))):
            if not available:
                break
            pos = available.pop(0)
            if pos not in used:
                positions['hard'].append(pos)
                used.add(pos)
        
        # 3. Kırılabilir duvarları yerleştir
        # Dinamik: Seviye arttıkça duvar sayısı artsın ama toplam 15'i geçmesin
        # Level 1-2: 8, Level 3: 9, Level 4: 10, ... Level 10+: 12 (maksimum)
        # Formula: min(8 + (level_number - 1), 12)
        max_breakable = min(8 + (level_number - 1), 12)
        max_total_walls = 15
        breakable_count = min(max_breakable, max_total_walls - hard_count)
        
        for _ in range(min(breakable_count, len(available))):
            if not available:
                break
            pos = available.pop(0)
            if pos not in used:
                positions['breakable'].append(pos)
                used.add(pos)
        
        return positions
    
    @staticmethod
    def _calculate_available_positions(width: int, height: int) -> list[Tuple[int, int]]:
        """
        Kullanılabilir pozisyonları hesaplar (grid pattern dışındaki tüm pozisyonlar).
        Grid pattern: x % 2 == 0 ve y % 2 == 0 (y >= 2)
        """
        available: list[Tuple[int, int]] = []
        for y in range(height):
            for x in range(width):
                # Dış duvarlar hariç
                if y == 0 or y == height - 1:
                    continue
                if x == 0 or x == width - 1:
                    continue
                # Grid pattern (şah tahtası deseni) hariç
                if x % 2 == 0 and y % 2 == 0 and y >= 2:
                    continue
                available.append((x, y))
        return available
    
    @staticmethod
    def _generate_seed(level_id: str) -> int:
        """Deterministik seed"""
        hash_obj = hashlib.md5(level_id.encode())
        return int(hash_obj.hexdigest(), 16) % (2**31)

