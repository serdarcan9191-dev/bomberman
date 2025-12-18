"""
Backend Level Service: Level bilgilerini yükler ve cache'ler
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
from pathlib import Path
from typing import Optional

from models.level import LevelData, TileType

logger = logging.getLogger(__name__)

# Level cache
_LEVEL_CACHE: dict[str, LevelData] = {}


def _load_level_from_json(level_id: str) -> Optional[LevelData]:
    """Level bilgilerini JSON'dan yükle"""
    try:
        # Client'taki levels.json dosyasını oku
        # Backend ve client aynı proje içinde olduğu için relative path kullan
        current_dir = Path(__file__).parent.parent.parent
        levels_json_path = current_dir / "bomberman" / "data" / "levels.json"
        
        if not levels_json_path.exists():
            logger.error(f"Levels JSON not found: {levels_json_path}")
            return None
        
        with open(levels_json_path, 'r', encoding='utf-8') as f:
            levels_data = json.load(f)
        
        # İstenen level'ı bul
        level_def = None
        for level in levels_data:
            if level.get("id") == level_id:
                level_def = level
                break
        
        if not level_def:
            logger.error(f"Level {level_id} not found in JSON")
            return None
        
        # Level bilgilerini parse et
        width = level_def.get("width", 11)
        height = level_def.get("height", 9)
        
        # Tile map oluştur - MapGenerator ile aynı mantık
        tiles: dict[tuple[int, int], TileType] = {}
        
        # 1. Tüm haritayı EMPTY ile başlat
        for y in range(height):
            for x in range(width):
                tiles[(x, y)] = TileType.EMPTY
        
        # 2. Sabit duvarlar: Üst ve alt satırlar (UNBREAKABLE)
        for x in range(width):
            tiles[(x, 0)] = TileType.UNBREAKABLE
            tiles[(x, height - 1)] = TileType.UNBREAKABLE
        
        # 3. Grid pattern: Çift x ve çift y koordinatlarında UNBREAKABLE (2'den başlayarak)
        # MapGenerator mantığı: x=0,2,4,6... ve y=2,4,6... (y=0 ve y=height-1 zaten border)
        for x in range(0, width, 2):
            for y in range(2, height - 1, 2):
                tiles[(x, y)] = TileType.UNBREAKABLE
        
        # 4. Ekstra sabit duvarlar (extra_unbreakable)
        extra_unbreakable = level_def.get("extra_unbreakable", [])
        for pos in extra_unbreakable:
            if isinstance(pos, list) and len(pos) >= 2:
                x, y = pos[0], pos[1]
                if 0 <= x < width and 0 <= y < height:
                    tiles[(x, y)] = TileType.UNBREAKABLE
        
        # 5. Hard duvarlar - Client ile aynı mantık (MapGenerator.generate_positions)
        # JSON'da hard_positions yoksa, client ile aynı seed ile oluştur
        hard_positions = level_def.get("hard_positions", [])
        if not hard_positions:
            # Client ile aynı seed mantığını kullan
            level_number = 1
            try:
                level_number = int(level_id.split("_")[-1])
            except (ValueError, IndexError):
                pass
            
            # Client ile aynı seed (MapGenerator._generate_seed mantığı - MD5 hash)
            hash_obj = hashlib.md5(level_id.encode())
            seed = int(hash_obj.hexdigest(), 16) % (2**31)
            rng = random.Random(seed)
            
            # Kullanılabilir pozisyonlar - Client ile aynı mantık
            available = []
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    # Grid pattern kontrolü: çift x ve çift y olmamalı (zaten UNBREAKABLE)
                    if not (x % 2 == 0 and y % 2 == 0):
                        if tiles.get((x, y)) == TileType.EMPTY:
                            available.append((x, y))
            
            # Oyuncu başlangıç pozisyonu ve çevresini hariç tut (client ile aynı)
            player_start = level_def.get("player_start", [1, 1])
            player_x, player_y = player_start[0], player_start[1]
            exclude = set()
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) <= 2:  # Manhattan distance <= 2
                        x, y = player_x + dx, player_y + dy
                        if 0 <= x < width and 0 <= y < height:
                            exclude.add((x, y))
            
            available = [pos for pos in available if pos not in exclude]
            rng.shuffle(available)
            
            # Hard duvarları yerleştir (client mantığı: level_number'a göre)
            # Seviye 1-3: 0, Seviye 4-5: 1, Seviye 6-7: 2, Seviye 8+: 3 (maksimum)
            hard_count = max(0, min((level_number - 1) // 2, 3))
            used = set()
            
            for _ in range(min(hard_count, len(available))):
                if not available:
                    break
                pos = available.pop(0)
                if pos not in used:
                    hard_positions.append(list(pos))
                    used.add(pos)
        
        # Hard duvarları yerleştir
        for pos in hard_positions:
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                x, y = pos[0], pos[1]
                if 0 <= x < width and 0 <= y < height:
                    if tiles.get((x, y)) == TileType.EMPTY:
                        tiles[(x, y)] = TileType.HARD
        
        # 6. Breakable duvarlar - Client ile aynı mantık (MapGenerator.generate_positions)
        # JSON'da breakable_positions yoksa, client ile aynı seed ile oluştur
        breakable_positions = level_def.get("breakable_positions", [])
        if not breakable_positions:
            # Client ile aynı seed mantığını kullan
            level_number = 1
            try:
                level_number = int(level_id.split("_")[-1])
            except (ValueError, IndexError):
                pass
            
            # Düşman sayısını hesapla
            enemy_spawns = level_def.get("enemy_spawns", [])
            enemy_count = sum(spawn.get("count", 0) for spawn in enemy_spawns)
            
            # Client ile aynı seed (MapGenerator._generate_seed mantığı - MD5 hash)
            hash_obj = hashlib.md5(level_id.encode())
            seed = int(hash_obj.hexdigest(), 16) % (2**31)
            rng = random.Random(seed)
            
            # Kullanılabilir pozisyonlar - Client ile aynı mantık
            # Grid pattern dışındaki tüm pozisyonlar (MapGenerator._calculate_available_positions)
            available = []
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    # Grid pattern kontrolü: çift x ve çift y olmamalı (zaten UNBREAKABLE)
                    if not (x % 2 == 0 and y % 2 == 0):
                        if tiles.get((x, y)) == TileType.EMPTY:
                            available.append((x, y))
            
            # Oyuncu başlangıç pozisyonu ve çevresini hariç tut (client ile aynı)
            player_start = level_def.get("player_start", [1, 1])
            player_x, player_y = player_start[0], player_start[1]
            exclude = set()
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) <= 2:  # Manhattan distance <= 2
                        x, y = player_x + dx, player_y + dy
                        if 0 <= x < width and 0 <= y < height:
                            exclude.add((x, y))
            
            available = [pos for pos in available if pos not in exclude]
            rng.shuffle(available)
            
            # Hard duvarları önce yerleştir (client mantığı)
            hard_count = max(0, min((level_number - 1) // 2, 3))
            used = set()
            hard_positions_list = level_def.get("hard_positions", [])
            if not hard_positions_list:
                for _ in range(min(hard_count, len(available))):
                    if not available:
                        break
                    pos = available.pop(0)
                    if pos not in used:
                        hard_positions_list.append(list(pos))
                        used.add(pos)
                        if tiles.get(pos) == TileType.EMPTY:
                            tiles[pos] = TileType.HARD
            
            # Breakable sayısı (client ile aynı mantık)
            max_breakable = min(8 + (level_number - 1), 12)
            max_total_walls = 15
            breakable_count = min(max_breakable, max_total_walls - hard_count)
            breakable_count = min(breakable_count, len(available))
            
            # Rastgele breakable pozisyonları seç
            for _ in range(breakable_count):
                if not available:
                    break
                pos = available.pop(0)
                if pos not in used:
                    breakable_positions.append(list(pos))
                    used.add(pos)
        
        # Breakable duvarları yerleştir
        for pos in breakable_positions:
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                x, y = pos[0], pos[1]
                if 0 <= x < width and 0 <= y < height:
                    if tiles.get((x, y)) == TileType.EMPTY:
                        tiles[(x, y)] = TileType.BREAKABLE
        
        # 7. Exit position (EMPTY veya BREAKABLE üzerine olmalı)
        exit_pos = level_def.get("exit_position", [])
        if isinstance(exit_pos, list) and len(exit_pos) >= 2:
            x, y = exit_pos[0], exit_pos[1]
            if 0 <= x < width and 0 <= y < height:
                # Exit sadece EMPTY veya BREAKABLE üzerine konabilir
                current_tile = tiles.get((x, y))
                if current_tile in (TileType.EMPTY, TileType.BREAKABLE):
                    tiles[(x, y)] = TileType.EXIT
                else:
                    # Geçersiz exit pozisyonu - en yakın EMPTY bul
                    logger.warning(f"Exit position ({x}, {y}) is not valid, finding nearest EMPTY")
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < width and 0 <= ny < height:
                                if tiles.get((nx, ny)) == TileType.EMPTY:
                                    tiles[(nx, ny)] = TileType.EXIT
                                    break
                        else:
                            continue
                        break
        
        level_data = LevelData(
            level_id=level_id,
            width=width,
            height=height,
            tiles=tiles
        )
        
        logger.info(f"Level {level_id} loaded: {width}x{height}, {len(tiles)} tiles")
        return level_data
        
    except Exception as e:
        logger.error(f"Error loading level {level_id}: {e}", exc_info=True)
        return None


def get_level(level_id: str) -> Optional[LevelData]:
    """Level bilgisini al (cache'den veya yükle)"""
    if level_id in _LEVEL_CACHE:
        return _LEVEL_CACHE[level_id]
    
    level_data = _load_level_from_json(level_id)
    if level_data:
        _LEVEL_CACHE[level_id] = level_data
    
    return level_data


def get_level_definition(level_id: str) -> Optional[dict]:
    """
    Level definition'ını JSON'dan al (enemy_spawns, enemy_positions vb. için).
    
    Args:
        level_id: Level ID
        
    Returns:
        Level definition dict veya None
    """
    try:
        current_dir = Path(__file__).parent.parent.parent
        levels_json_path = current_dir / "bomberman" / "data" / "levels.json"
        
        if not levels_json_path.exists():
            logger.error(f"Levels JSON not found: {levels_json_path}")
            return None
        
        with open(levels_json_path, 'r', encoding='utf-8') as f:
            levels_data = json.load(f)
        
        # İstenen level'ı bul
        for level in levels_data:
            if level.get("id") == level_id:
                return level
        
        logger.error(f"Level {level_id} not found in JSON")
        return None
    except Exception as e:
        logger.error(f"Error loading level definition {level_id}: {e}", exc_info=True)
        return None

