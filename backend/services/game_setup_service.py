"""
Game Setup Service: Oyun başlatma, harita yükleme, düşman spawn, oyuncu pozisyonlama
Single Responsibility: Oyun başlatma ile ilgili tüm setup işlemleri
"""
from __future__ import annotations

import hashlib
import logging
import random
from typing import Optional

from models.level import TileType
from models.room import Enemy, GameRoom
from services.level_service import get_level, get_level_definition

logger = logging.getLogger(__name__)


class GameSetupService:
    """Oyun başlatma ve setup işlemleri için helper service."""
    
    def __init__(self):
        """Game setup service başlat."""
        pass
    
    def load_level(self, room: GameRoom) -> bool:
        """
        Level bilgisini yükle ve room'a set et.
        
        Args:
            room: Oyun odası
            
        Returns:
            bool: Başarılı mı?
        """
        level_data = get_level(room.level_id)
        if not level_data:
            logger.error(f"Level {room.level_id} not found! Oyun başlatılamaz.")
            return False
        
        room.level_data = level_data
        room.level_width = level_data.width
        room.level_height = level_data.height
        
        # Orijinal breakable wall pozisyonlarını kaydet (destroyed_walls hesaplaması için)
        room.original_breakable_walls = {
            (x, y) for (x, y), tile_type in level_data.tiles.items()
            if tile_type == TileType.BREAKABLE
        }
        
        logger.info(f"Level {room.level_id} loaded: {level_data.width}x{level_data.height}, {len(room.original_breakable_walls)} breakable walls")
        return True
    
    def spawn_enemies(self, room: GameRoom) -> None:
        """
        Düşmanları spawn et (level'den enemy_spawns ve enemy_positions al).
        
        Args:
            room: Oyun odası
        """
        if not room.level_data:
            logger.warning(f"Cannot spawn enemies: level_data not loaded for room {room.room_id}")
            return
        
        room.enemies = []
        
        # Level definition'ı level_service'den al (duplicate JSON okumayı önlemek için)
        level_def = get_level_definition(room.level_id)
        if not level_def:
            logger.warning(f"Level definition not found for {room.level_id}")
            return
        
        enemy_spawns = level_def.get("enemy_spawns", [])
        enemy_positions = level_def.get("enemy_positions", [])
        
        # Eğer enemy_positions yoksa, hesapla (client ile aynı mantık)
        if not enemy_positions:
            enemy_positions = self._calculate_enemy_positions(
                room.level_id,
                room.level_data,
                enemy_spawns
            )
        
        # Düşmanları spawn et
        positions_iter = iter(enemy_positions)
        enemy_id_counter = 0
        
        for spawn in enemy_spawns:
            enemy_type = spawn.get("type", "CHASING").lower()  # "STATIC", "CHASING", "SMART"
            count = spawn.get("count", 0)
            
            for _ in range(count):
                try:
                    pos_tuple = next(positions_iter)
                    if isinstance(pos_tuple, list) and len(pos_tuple) >= 2:
                        pos = (pos_tuple[0], pos_tuple[1])
                    elif isinstance(pos_tuple, tuple) and len(pos_tuple) >= 2:
                        pos = pos_tuple
                    else:
                        continue
                    
                    # Geçerli pozisyon kontrolü
                    if not room.level_data.can_move_to(pos[0], pos[1]):
                        continue
                    
                    enemy = Enemy(
                        enemy_id=f"enemy_{enemy_id_counter}",
                        enemy_type=enemy_type,
                        position=pos,
                        spawn_position=pos,  # Doğduğu pozisyonu kaydet
                        health=100,
                        alive=True,
                        last_move_time=0.0
                    )
                    room.enemies.append(enemy)
                    enemy_id_counter += 1
                    logger.info(f"Spawned {enemy_type} enemy at {pos}")
                except StopIteration:
                    break
        
        logger.info(f"Spawned {len(room.enemies)} enemies in room {room.room_id}")
    
    def position_players(self, room: GameRoom) -> None:
        """
        Oyunculara başlangıç pozisyonlarını ver - YAN YANA.
        
        Args:
            room: Oyun odası
        """
        if not room.level_data:
            logger.warning(f"Cannot position players: level_data not loaded for room {room.room_id}")
            return
        
        # Player 1: sol üst (1, 1) veya geçerli bir pozisyon
        if len(room.players) >= 1:
            pos1 = (1, 1)
            if not room.level_data.can_move_to(pos1[0], pos1[1]):
                # Geçerli bir pozisyon bul
                for y in range(1, room.level_height - 1):
                    for x in range(1, room.level_width - 1):
                        if room.level_data.can_move_to(x, y):
                            pos1 = (x, y)
                            break
                    if pos1 != (1, 1):
                        break
            room.players[0].position = pos1
            logger.info(f"Player 1 ({room.players[0].username}) başlangıç pozisyonu: {pos1}")
        
        # Player 2: Player 1'in yanında bir pozisyon
        if len(room.players) >= 2:
            pos1 = room.players[0].position
            pos2 = None
            
            # Önce sağa bak (x+1, y)
            candidate_positions = [
                (pos1[0] + 1, pos1[1]),  # Sağ
                (pos1[0] - 1, pos1[1]),  # Sol
                (pos1[0], pos1[1] + 1),  # Alt
                (pos1[0], pos1[1] - 1),  # Üst
            ]
            
            # Geçerli bir pozisyon bul
            for candidate in candidate_positions:
                if (room.level_data.can_move_to(candidate[0], candidate[1]) and 
                    candidate != pos1):
                    pos2 = candidate
                    break
            
            # Eğer yanında geçerli pozisyon yoksa, biraz daha uzakta ara
            if not pos2:
                for y in range(1, room.level_height - 1):
                    for x in range(1, room.level_width - 1):
                        if (room.level_data.can_move_to(x, y) and 
                            (x, y) != pos1 and
                            abs(x - pos1[0]) + abs(y - pos1[1]) <= 3):  # Maksimum 3 tile uzaklık
                            pos2 = (x, y)
                            break
                    if pos2:
                        break
            
            if not pos2:
                # Fallback: sağ alt köşe
                pos2 = (room.level_width - 2, room.level_height - 2)
            
            room.players[1].position = pos2
            logger.info(f"Player 2 ({room.players[1].username}) başlangıç pozisyonu: {pos2} (Player 1: {pos1})")
    
    def _calculate_enemy_positions(
        self,
        level_id: str,
        level_data,
        enemy_spawns: list[dict]
    ) -> list[tuple[int, int]]:
        """
        Düşman pozisyonlarını hesapla (client ile aynı mantık).
        
        Args:
            level_id: Level ID
            level_data: LevelData objesi
            enemy_spawns: Enemy spawn tanımları
            
        Returns:
            Enemy pozisyonları listesi
        """
        total_enemies = sum(spawn.get("count", 0) for spawn in enemy_spawns)
        if total_enemies == 0:
            return []
        
        # Client ile aynı seed mantığı
        level_number = 1
        try:
            level_number = int(level_id.split("_")[-1])
        except (ValueError, IndexError):
            pass
        
        hash_obj = hashlib.md5(level_id.encode())
        seed = int(hash_obj.hexdigest(), 16) % (2**31)
        rng = random.Random(seed)
        
        # Kullanılabilir pozisyonlar
        available = []
        for y in range(1, level_data.height - 1):
            for x in range(1, level_data.width - 1):
                if not (x % 2 == 0 and y % 2 == 0):  # Grid pattern dışı
                    if level_data.can_move_to(x, y):
                        available.append((x, y))
        
        # Oyuncu başlangıç pozisyonu ve çevresini hariç tut
        player_start = (1, 1)  # Default
        exclude = set()
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if abs(dx) + abs(dy) <= 2:
                    x, y = player_start[0] + dx, player_start[1] + dy
                    if 0 <= x < level_data.width and 0 <= y < level_data.height:
                        exclude.add((x, y))
        
        available = [pos for pos in available if pos not in exclude]
        rng.shuffle(available)
        
        # Düşman pozisyonları: Oyuncudan minimum 3 uzaklıkta
        enemy_positions = []
        used = set()
        
        for pos in available:
            if len(enemy_positions) >= total_enemies:
                break
            if pos in used:
                continue
            
            # Oyuncudan uzaklık kontrolü
            distance = abs(pos[0] - player_start[0]) + abs(pos[1] - player_start[1])
            if distance >= 3:
                enemy_positions.append(pos)
                used.add(pos)
        
        # Eğer yeterli pozisyon bulunamadıysa, uzaklık şartını kaldır
        if len(enemy_positions) < total_enemies:
            for pos in available:
                if len(enemy_positions) >= total_enemies:
                    break
                if pos not in used:
                    enemy_positions.append(pos)
                    used.add(pos)
        
        return enemy_positions[:total_enemies]

